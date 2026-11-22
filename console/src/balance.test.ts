// Tests sessions.csv parsing, whole_chip hour splitting, and 10% track-balance flags.
import { describe, expect, it } from "vitest";
import { computeBalance, parseSessionsCsv } from "./balance";

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
});
