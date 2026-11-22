// Parses tracking/sessions.csv and computes per-track hours, passing check counts, and 10% behind-leader flags matching tracking/balance.py.
import { TRACKS, type TrackId } from "./catalog";
import type { CheckRow } from "./summary";

export type CoreTrack = "digital" | "analog" | "ams";

export interface TrackBalance {
  track: CoreTrack;
  label: string;
  hours: number;
  passedChecks: number;
  behindHours: boolean;
  behindChecks: boolean;
}

const PROJECT_TRACK: Record<string, TrackId> = Object.fromEntries(
  TRACKS.flatMap((t) => t.blocks.map((b) => [b.id, t.id]))
);

export function parseSessionsCsv(csvText: string): Record<CoreTrack, number> {
  const hours: Record<CoreTrack, number> = { digital: 0, analog: 0, ams: 0 };
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length < 2) return hours;
  const header = lines[0].split(",").map((s) => s.trim());
  const projIdx = header.indexOf("project");
  const hrsIdx = header.indexOf("hours");
  if (projIdx === -1 || hrsIdx === -1) return hours;
  for (const line of lines.slice(1)) {
    if (!line.trim()) continue;
    const cols = line.split(",");
    const proj = (cols[projIdx] ?? "").trim();
    const h = Number.parseFloat((cols[hrsIdx] ?? "0").trim());
    if (!Number.isFinite(h) || h <= 0) continue;
    if (proj === "whole_chip") {
      hours.digital += h / 3;
      hours.analog += h / 3;
      hours.ams += h / 3;
    } else {
      const tr = PROJECT_TRACK[proj];
      if (tr === "digital" || tr === "analog" || tr === "ams") hours[tr] += h;
    }
  }
  return hours;
}

export function computeBalance(
  hours: Record<CoreTrack, number>,
  summaries: Record<string, CheckRow[] | null>
): TrackBalance[] {
  const tracks: { id: CoreTrack; label: string }[] = [
    { id: "digital", label: "Digital VLSI" },
    { id: "analog", label: "Analog VLSI" },
    { id: "ams", label: "Analog / Mixed-Signal" },
  ];
  const counts: Record<CoreTrack, number> = { digital: 0, analog: 0, ams: 0 };
  for (const t of TRACKS) {
    if (t.id !== "digital" && t.id !== "analog" && t.id !== "ams") continue;
    for (const b of t.blocks) {
      const rows = summaries[b.id];
      if (rows) counts[t.id] += rows.filter((r) => r.result === "pass").length;
    }
  }
  const maxH = Math.max(hours.digital, hours.analog, hours.ams);
  const maxC = Math.max(counts.digital, counts.analog, counts.ams);
  return tracks.map((t) => ({
    track: t.id,
    label: t.label,
    hours: Number(hours[t.id].toFixed(2)),
    passedChecks: counts[t.id],
    behindHours: maxH > 0 && hours[t.id] < maxH * 0.9 - 1e-9,
    behindChecks: maxC > 0 && counts[t.id] < maxC * 0.9 - 1e-9,
  }));
}
