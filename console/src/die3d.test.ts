// Regression guard ensuring Die3DView never tears down its WebGLRenderer on mouse-move re-renders from App.
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("Die3DView WebGL lifecycle guard", () => {
  it("memoizes onSelectBlockLayout in App and excludes it from Die3DView renderer useEffect deps", () => {
    const appSrc = fs.readFileSync(path.resolve(__dirname, "App.tsx"), "utf8");
    const dieSrc = fs.readFileSync(path.resolve(__dirname, "Die3DView.tsx"), "utf8");
    expect(appSrc).toMatch(/useCallback\(/);
    expect(appSrc).toMatch(/onSelectBlockLayout=\{handleSelectBlockLayout\}/);
    expect(dieSrc).toMatch(/\},\s*\[summaries,\s*reducedMotion\]\);/);
    expect(dieSrc).not.toMatch(/\[summaries,\s*reducedMotion,\s*onSelectBlockLayout\]/);
  });
});
