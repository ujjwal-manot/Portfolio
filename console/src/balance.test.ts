// Tests sessions.csv parsing (including RFC-4180 quotes and UTF-8 BOM), whole_chip hour splitting, real repo summary balance parity, and 10% track-balance flags.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { computeBalance, parseSessionsCsv } from "./balance";
import { parseSummary, type CheckRow } from "./summary";

describe("balance helpers", () => {
  it("splits whole_chip hours evenly across the three tracks and flags tracks >10% behind", () => {
    const csv = [
      "date,project,track,hours,energy,lost_track_of_time,extra_work,best,worst",
      "2026-11-22,cpu,digital,6,4,no,no,a,b",
      "2026-11-22,opamp,analog,6,4,no,no,a,b",
      "2026-11-22,adc,ams,3,4,no,no,a,b",
      "2026-11-22,whole_chip,whole_chip,3,4,no,no,a,b",
    ].join("\n");
    const hours = parseSessionsCsv(csv);
    expect(hours).toEqual({ digital: 7, analog: 7, ams: 4 });
    const rows = computeBalance(hours, {
      cpu: [{ name: "t1", result: "pass", time: "", logs: [], sourceCount: 1 }],
      opamp: [{ name: "t1", result: "pass", time: "", logs: [], sourceCount: 1 }],
      adc: null,
    });
    expect(rows.find((r) => r.track === "ams")?.behindHours).toBe(true);
    expect(rows.find((r) => r.track === "ams")?.behindChecks).toBe(true);
    expect(rows.find((r) => r.track === "analog")?.behindHours).toBe(false);
  });

  it("handles UTF-8 BOM, CRLF endings, and RFC-4180 quoted CSV fields from log_session.py", () => {
    const csv = [
      '\uFEFF"notes",date,"project",track,"hours",best,worst',
      '"phase 1, rev A",2026-11-22,"cpu",digital,"4.5","closed 50 MHz, 0 holds","slow synth"',
      '"phase 1, rev B",2026-11-22,"opamp",analog,"4.5","60 corners, 100% yield","none"',
      '"phase 1, rev C",2026-11-22,"whole_chip",all,"3.0","cosim, dvfs","none"',
    ].join("\r\n");
    const hours = parseSessionsCsv(csv);
    expect(hours).toEqual({ digital: 5.5, analog: 5.5, ams: 1.0 });
  });

  it("computes track check balance cleanly on real repo summary.json files", () => {
    const repoRoot = path.resolve(__dirname, "../..");
    const summaries: Record<string, CheckRow[] | null> = {};
    for (const block of ["cpu", "fifo_bridge", "opamp", "adc", "power_manager"]) {
      const p = path.join(repoRoot, "projects", block, "results", "summary.json");
      summaries[block] = parseSummary(JSON.parse(fs.readFileSync(p, "utf8")));
    }
    const rows = computeBalance({ digital: 10, analog: 10, ams: 10 }, summaries);
    const byTrack = Object.fromEntries(rows.map((r) => [r.track, r]));
    expect(byTrack.digital.passedChecks).toBeGreaterThan(50);
    expect(byTrack.analog.passedChecks).toBeGreaterThan(0);
    expect(byTrack.ams.passedChecks).toBeGreaterThan(0);
    expect(byTrack.digital.behindChecks).toBe(false);
    expect(byTrack.analog.behindChecks).toBe(true);
    expect(byTrack.ams.behindChecks).toBe(true);
  });
});
