// Tests summary.json parsing, not-run status handling, and SHA-256 command log generation on a small fixture.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { blockStatus, commandLogFromSummary, parseSummary } from "./summary";

describe("parseSummary", () => {
  it("parses check rows sorted by name and extracts log hashes", () => {
    const raw = JSON.parse(fs.readFileSync(path.resolve(__dirname, "fixtures/sample_summary.json"), "utf8"));
    const rows = parseSummary(raw);
    expect(rows.map((r) => r.name)).toEqual(["cdc", "timing_slow"]);
    expect(rows[0].result).toBe("fail");
    expect(rows[1].result).toBe("pass");
    expect(rows[1].logs[0].sha256).toHaveLength(64);
    expect(rows[1].sourceCount).toBe(1);
    expect(blockStatus(rows)).toBe("fail");
    const cmd = commandLogFromSummary("cpu", rows);
    expect(cmd).toHaveLength(2);
    expect(cmd[0].path).toBe("projects/cpu/results/cdc.log");
  });

  it("reports not run when summary.json is missing or empty", () => {
    expect(blockStatus(null)).toBe("not run");
    expect(blockStatus([])).toBe("not run");
  });

  it("rejects non-object summary payloads", () => {
    expect(() => parseSummary([])).toThrow();
    expect(() => parseSummary(null)).toThrow();
  });
});
