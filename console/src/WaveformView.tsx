// Renders ngspice .raw waveforms in uPlot on a black canvas with two click cursors and delta readout.
import { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import { parseNgspiceRaw, type RawWaveform } from "./raw";

const TRACE_COLORS = ["#4aa3ff", "#35c47c", "#f5a524", "#e066ff", "#ff6b6b", "#5ce1e6"];

interface WaveformViewProps {
  block: string;
  rawFiles: string[];
}

export function WaveformView({ block, rawFiles }: WaveformViewProps) {
  const plotRef = useRef<HTMLDivElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<string>(rawFiles[0] ?? "");
  const [wave, setWave] = useState<RawWaveform | null>(null);
  const [error, setError] = useState<string>("");
  const [c1, setC1] = useState<number | null>(null);
  const [c2, setC2] = useState<number | null>(null);
  const nextCursor = useRef<1 | 2>(1);

  useEffect(() => {
    setSelectedFile(rawFiles[0] ?? "");
    setWave(null);
    setC1(null);
    setC2(null);
    setError("");
  }, [block, rawFiles]);

  useEffect(() => {
    if (!selectedFile) return;
    let active = true;
    fetch(`/repo/projects/${block}/results/${selectedFile}`)
      .then((res) => (res.ok ? res.arrayBuffer() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((buf) => {
        if (!active) return;
        setWave(parseNgspiceRaw(buf));
        setError("");
        setC1(null);
        setC2(null);
      })
      .catch((e: unknown) => {
        if (active) setError(e instanceof Error ? e.message : "failed to load .raw");
      });
    return () => {
      active = false;
    };
  }, [block, selectedFile]);

  useEffect(() => {
    const el = plotRef.current;
    if (!el || !wave || wave.data.length < 2) return;
    el.innerHTML = "";
    const series: uPlot.Series[] = [
      { label: wave.variables[0].name },
      ...wave.variables.slice(1, 7).map((v, i) => ({
        label: v.name,
        stroke: TRACE_COLORS[i % TRACE_COLORS.length],
        width: 1.5,
      })),
    ];
    const plotData: uPlot.AlignedData = [
      wave.data[0],
      ...wave.data.slice(1, 7),
    ];
    const plot = new uPlot(
      {
        width: Math.max(520, el.clientWidth - 8),
        height: 360,
        series,
        axes: [
          { stroke: "#7f8ca0", grid: { stroke: "#1c222d" } },
          { stroke: "#7f8ca0", grid: { stroke: "#1c222d" } },
        ],
        hooks: {
          init: [
            (u) => {
              u.over.addEventListener("click", () => {
                const idx = u.cursor.idx;
                if (idx == null) return;
                if (nextCursor.current === 1) {
                  setC1(idx);
                  nextCursor.current = 2;
                } else {
                  setC2(idx);
                  nextCursor.current = 1;
                }
              });
            },
          ],
        },
      },
      plotData,
      el
    );
    return () => plot.destroy();
  }, [wave]);

  const x0 = wave && c1 != null ? wave.data[0][c1] : null;
  const x1 = wave && c2 != null ? wave.data[0][c2] : null;
  const y0 = wave && c1 != null ? wave.data[1]?.[c1] ?? null : null;
  const y1 = wave && c2 != null ? wave.data[1]?.[c2] ?? null : null;
  const dx = x0 != null && x1 != null ? x1 - x0 : null;
  const dy = y0 != null && y1 != null ? y1 - y0 : null;

  return (
    <section className="results-card">
      <div className="results-head">
        <strong>{block} / Waveforms (ngspice .raw)</strong>
        <div className="tabs">
          {rawFiles.length > 0 && (
            <select
              className="small-btn"
              value={selectedFile}
              onChange={(e) => setSelectedFile(e.target.value)}
            >
              {rawFiles.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          )}
          <label className="small-btn">
            Load local .raw
            <input
              type="file"
              accept=".raw"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                file.arrayBuffer().then((buf) => {
                  try {
                    setWave(parseNgspiceRaw(buf));
                    setError("");
                    setC1(null);
                    setC2(null);
                  } catch (err: unknown) {
                    setError(err instanceof Error ? err.message : "parse error");
                  }
                });
              }}
            />
          </label>
        </div>
      </div>

      {error && <p className="err-text">{error}</p>}
      {!wave && !error && (
        <p>
          No .raw files found in projects/{block}/results/ (large .raw files are gitignored; run simulation locally or open a local .raw file above).
        </p>
      )}
      {wave && (
        <>
          <div className="cursor-bar">
            <span>Plot: {wave.plotname || wave.title}</span>
            <span>C1: {x0 != null ? `${x0.toExponential(3)}, ${y0?.toExponential(3)}` : "click trace"}</span>
            <span>C2: {x1 != null ? `${x1.toExponential(3)}, ${y1?.toExponential(3)}` : "click trace"}</span>
            <span>
              Delta: {dx != null && dy != null ? `dx=${dx.toExponential(3)} dy=${dy.toExponential(3)}` : "n/a"}
            </span>
          </div>
          <div ref={plotRef} className="uplot-host" />
        </>
      )}
    </section>
  );
}
