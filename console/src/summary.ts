// Parses projects/<block>/results/summary.json into typed check rows, overall block status, and SHA-256 command log items.
export type BlockStatus = "not run" | "pass" | "fail";

export interface LogHash {
  file: string;
  sha256: string;
}

export interface CheckRow {
  name: string;
  result: "pass" | "fail";
  time: string;
  logs: LogHash[];
  sourceCount: number;
}

export interface CommandLogItem {
  path: string;
  sha256: string;
  note: string;
}

interface RawEntry {
  result?: unknown;
  time?: unknown;
  logs?: Record<string, unknown>;
  sources?: Record<string, unknown>;
}

export function parseSummary(raw: unknown): CheckRow[] {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error("summary.json must be a JSON object");
  }
  const rows: CheckRow[] = [];
  for (const [name, value] of Object.entries(raw as Record<string, RawEntry>)) {
    if (!value || typeof value !== "object" || Array.isArray(value)) continue;
    const result = value.result === "pass" ? "pass" : "fail";
    const time = typeof value.time === "string" ? value.time : "";
    const logs: LogHash[] = [];
    if (value.logs && typeof value.logs === "object" && !Array.isArray(value.logs)) {
      for (const [file, digest] of Object.entries(value.logs)) {
        if (typeof digest === "string") logs.push({ file, sha256: digest });
      }
    }
    const sourceCount =
      value.sources && typeof value.sources === "object" && !Array.isArray(value.sources)
        ? Object.keys(value.sources).length
        : 0;
    rows.push({ name, result, time, logs, sourceCount });
  }
  return rows.sort((a, b) => a.name.localeCompare(b.name));
}

export function blockStatus(rows: CheckRow[] | null): BlockStatus {
  if (!rows || rows.length === 0) return "not run";
  return rows.every((r) => r.result === "pass") ? "pass" : "fail";
}

export function commandLogFromSummary(block: string, rows: CheckRow[]): CommandLogItem[] {
  const seen = new Set<string>();
  const items: CommandLogItem[] = [];
  for (const row of rows) {
    for (const log of row.logs) {
      const fullPath = `projects/${block}/results/${log.file}`;
      if (seen.has(fullPath)) continue;
      seen.add(fullPath);
      items.push({ path: fullPath, sha256: log.sha256, note: row.name });
    }
  }
  return items;
}
