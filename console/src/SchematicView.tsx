// Read-only schematic SVG viewer with pan/zoom and an Open in xschem command copy helper.
import { useEffect, useState } from "react";

interface SchematicViewProps {
  block: string;
  svgFiles: string[];
  zoom: number;
}

export function SchematicView({ block, svgFiles, zoom }: SchematicViewProps) {
  const [svgMarkup, setSvgMarkup] = useState<string>("");
  const [copied, setCopied] = useState<boolean>(false);
  const selected = svgFiles[0] ?? "";
  const shellCmd = `xschem projects/${block}/design/${block}.sch`;

  useEffect(() => {
    setSvgMarkup("");
    if (!selected) return;
    let active = true;
    fetch(`/repo/projects/${block}/results/${selected}`)
      .then((res) => (res.ok ? res.text() : ""))
      .then((text) => {
        if (active) setSvgMarkup(text);
      })
      .catch(() => {
        if (active) setSvgMarkup("");
      });
    return () => {
      active = false;
    };
  }, [block, selected]);

  return (
    <section className="results-card">
      <div className="results-head">
        <strong>{block} / Schematic</strong>
        <button
          type="button"
          className="small-btn"
          onClick={() => {
            navigator.clipboard?.writeText(shellCmd).catch(() => {});
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Copied command" : "Open in xschem"}
        </button>
      </div>
      <div className="cmd-hint">Shell command (read-only viewer does not execute tools): <code>{shellCmd}</code></div>
      {svgMarkup ? (
        <div
          className="svg-stage"
          style={{ transform: `scale(${zoom / 100})`, transformOrigin: "top left" }}
          dangerouslySetInnerHTML={{ __html: svgMarkup }}
        />
      ) : (
        <p>No xschem SVG export found in projects/{block}/results/ yet.</p>
      )}
    </section>
  );
}
