// Tests the KLayout .lyp parser on a small fixture and on the pinned IHP sg13g2.lyp file.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { parseLyp } from "./lyp";

describe("parseLyp", () => {
  it("parses layer name, source, colors, dither, and visibility from fixture", () => {
    const xml = fs.readFileSync(path.resolve(__dirname, "fixtures/sample.lyp"), "utf8");
    const layers = parseLyp(xml);
    expect(layers).toHaveLength(2);
    expect(layers[0]).toMatchObject({
      name: "Activ.drawing",
      source: "1/0",
      fillColor: "#00ff00",
      frameColor: "#00ff00",
      dither: "C2",
      visible: true,
    });
    expect(layers[1]).toMatchObject({
      name: "Metal1.drawing",
      source: "8/0",
      visible: false,
    });
  });

  it("loads the pinned IHP sg13g2.lyp layer palette", () => {
    const xml = fs.readFileSync(path.resolve(__dirname, "../public/sg13g2.lyp"), "utf8");
    const layers = parseLyp(xml);
    expect(layers.length).toBeGreaterThan(100);
    expect(layers.some((l) => l.name === "Activ.drawing" && l.source === "1/0")).toBe(true);
  });
});
