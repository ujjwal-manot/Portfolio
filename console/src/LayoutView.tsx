// Read-only layout view wired to the active SG13G2 layer palette visibility state plus an Open in KLayout command helper.
import { useState } from "react";
import type { LayerEntry } from "./lyp";

interface LayoutViewProps {
  block: string;
  layers: LayerEntry[];
  zoom: number;
}

export function LayoutView({ block, layers, zoom }: LayoutViewProps) {
  const [copied, setCopied] = useState<boolean>(false);
  const visibleCount = layers.filter((l) => l.visible).length;
  const shellCmd = `klayout -l console/public/sg13g2.lyp projects/${block}/layout/${block}.gds`;

  return (
    <section className="results-card">
      <div className="results-head">
        <strong>{block} / Layout (SG13G2)</strong>
        <button
          type="button"
          className="small-btn"
          onClick={() => {
            navigator.clipboard?.writeText(shellCmd).catch(() => {});
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Copied command" : "Open in KLayout"}
        </button>
      </div>
      <div className="cmd-hint">Shell command (read-only viewer does not execute tools): <code>{shellCmd}</code></div>
      <p>
        Active SG13G2 layer palette: {visibleCount} of {layers.length} layers visible at {zoom}% zoom. Exported layout geometry JSON/SVG from KLayout attaches here once logged under projects/{block}/results/.
      </p>
    </section>
  );
}
