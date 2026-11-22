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

  it("parses real repo summary.json files (cpu, fifo_bridge, opamp) without errors or duplicate log paths", () => {
    const repoRoot = path.resolve(__dirname, "../..");
    for (const block of ["cpu", "fifo_bridge", "opamp"]) {
      const p = path.join(repoRoot, "projects", block, "results", "summary.json");
      const raw = JSON.parse(fs.readFileSync(p, "utf8"));
      const rows = parseSummary(raw);
      expect(rows.length).toBeGreaterThan(0);
      expect(blockStatus(rows)).toBe("pass");
      for (const row of rows) {
        expect(row.logs.length).toBeGreaterThan(0);
        for (const log of row.logs) {
          expect(log.sha256).toMatch(/^[0-9a-f]{64}$/);
        }
      }
      const cmd = commandLogFromSummary(block, rows);
      const uniquePaths = new Set(cmd.map((c) => c.path));
      expect(uniquePaths.size).toBe(cmd.length);
    }
  });

  it("ignores malformed array values inside summary entries", () => {
    const rows = parseSummary({
      bad_entry: ["not", "an", "object"],
      weird_fields: { result: "pass", time: "2026-11-22", logs: ["a"], sources: ["b"] },
    });
    expect(rows).toHaveLength(1);
    expect(rows[0].logs).toEqual([]);
    expect(rows[0].sourceCount).toBe(0);
  });
});
