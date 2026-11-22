// Tests ASCII and binary ngspice .raw waveform parsing in console/src/raw.ts.
import { describe, expect, it } from "vitest";
import { parseNgspiceRaw } from "./raw";

function toBuf(text: string): ArrayBuffer {
  const bytes = new TextEncoder().encode(text);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

describe("parseNgspiceRaw", () => {
  it("parses an ASCII transient .raw file", () => {
    const ascii = [
      "Title: opamp step",
      "Plotname: Transient Analysis",
      "Flags: real",
      "No. Variables: 2",
      "No. Points: 3",
      "Variables:",
      "\t0\ttime\ttime",
      "\t1\tv(out)\tvoltage",
      "Values:",
      " 0\t0.000000e+00",
      "\t6.000000e-01",
      " 1\t1.000000e-08",
      "\t8.500000e-01",
      " 2\t2.000000e-08",
      "\t1.000000e+00",
      "",
    ].join("\n");
    const w = parseNgspiceRaw(toBuf(ascii));
    expect(w.title).toBe("opamp step");
    expect(w.variables.map((v) => v.name)).toEqual(["time", "v(out)"]);
    expect(w.data[0]).toEqual([0, 1e-8, 2e-8]);
    expect(w.data[1]).toEqual([0.6, 0.85, 1.0]);
  });

  it("parses a binary IEEE-754 little-endian .raw file", () => {
    const header = [
      "Title: adc",
      "Plotname: Transient Analysis",
      "Flags: real",
      "No. Variables: 2",
      "No. Points: 2",
      "Variables:",
      "\t0\ttime\ttime",
      "\t1\tv(top)\tvoltage",
      "Binary:",
      "",
    ].join("\n");
    const hdrBytes = new TextEncoder().encode(header);
    const out = new Uint8Array(hdrBytes.length + 4 * 8);
    out.set(hdrBytes, 0);
    const dv = new DataView(out.buffer, hdrBytes.length);
    [0.0, 0.6, 5e-9, 0.25].forEach((val, i) => dv.setFloat64(i * 8, val, true));
    const w = parseNgspiceRaw(out.buffer);
    expect(w.data[0]).toEqual([0.0, 5e-9]);
    expect(w.data[1]).toEqual([0.6, 0.25]);
  });

  it("rejects malformed payloads without Values or Binary", () => {
    expect(() => parseNgspiceRaw(toBuf("Title: bad\n"))).toThrow();
  });

  it("rejects truncated binary .raw payloads with a descriptive error", () => {
    const header = [
      "Title: short",
      "Plotname: Transient Analysis",
      "Flags: real",
      "No. Variables: 2",
      "No. Points: 4",
      "Variables:",
      "\t0\ttime\ttime",
      "\t1\tv(out)\tvoltage",
      "Binary:",
      "",
    ].join("\n");
    const hdrBytes = new TextEncoder().encode(header);
    const shortBuf = new Uint8Array(hdrBytes.length + 8);
    shortBuf.set(hdrBytes, 0);
    expect(() => parseNgspiceRaw(shortBuf.buffer)).toThrow(/truncated/i);
  });
});
