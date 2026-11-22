// Read-only EdgeSense-130 console shell: library tree, SG13G2 layer palette, dot-grid canvas with Results view, SHA-256 command log, and status bar.
import { useEffect, useMemo, useState } from "react";
import { ALL_BLOCKS, TRACKS, VIEWS, type ViewId } from "./catalog";
import { BlockIcon, EyeIcon, TrackIcon } from "./icons";
import { parseLyp, type LayerEntry } from "./lyp";
import {
  blockStatus,
  commandLogFromSummary,
  parseSummary,
  type CheckRow,
  type CommandLogItem,
} from "./summary";

type SummaryMap = Record<string, CheckRow[] | null>;

function statusClass(status: string): string {
  return status === "not run" ? "not-run" : status;
}

export function App() {
  const [selectedBlock, setSelectedBlock] = useState<string>("cpu");
  const [selectedView, setSelectedView] = useState<ViewId>("results");
  const [summaries, setSummaries] = useState<SummaryMap>({});
  const [layers, setLayers] = useState<LayerEntry[]>([]);
  const [layerFilter, setLayerFilter] = useState<string>("");
  const [cursor, setCursor] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(100);
  const [systemLog, setSystemLog] = useState<CommandLogItem[]>([]);

  useEffect(() => {
    let active = true;
    fetch("/sg13g2.lyp")
      .then((res) => (res.ok ? res.text() : Promise.reject(new Error("sg13g2.lyp load failed"))))
      .then(async (xml) => {
        if (!active) return;
        const parsed = parseLyp(xml);
        const bytes = new TextEncoder().encode(xml);
        const hashBuf = await crypto.subtle.digest("SHA-256", bytes);
        const sha256 = Array.from(new Uint8Array(hashBuf), (b) => b.toString(16).padStart(2, "0")).join("");
        setLayers(parsed);
        setSystemLog((prev) => [
          ...prev,
          { path: "console/public/sg13g2.lyp", sha256, note: `${parsed.length} layers` },
        ]);
      })
      .catch(() => {
        if (active) setLayers([]);
      });

    Promise.all(
      ALL_BLOCKS.map(async (b) => {
        try {
          const res = await fetch(`/repo/projects/${b.id}/results/summary.json`);
          if (!res.ok) return [b.id, null] as const;
          const json: unknown = await res.json();
          return [b.id, parseSummary(json)] as const;
        } catch {
          return [b.id, null] as const;
        }
      })
    ).then((pairs) => {
      if (!active) return;
      const next: SummaryMap = {};
      for (const [id, rows] of pairs) next[id] = rows;
      setSummaries(next);
    });
    return () => {
      active = false;
    };
  }, []);

  const currentBlock = useMemo(
    () => ALL_BLOCKS.find((b) => b.id === selectedBlock) ?? ALL_BLOCKS[0],
    [selectedBlock]
  );
  const currentRows = summaries[currentBlock.id] ?? null;
  const currentStatus = blockStatus(currentRows);

  const commandLog = useMemo(() => {
    const items: CommandLogItem[] = [...systemLog];
    for (const block of ALL_BLOCKS) {
      const rows = summaries[block.id];
      if (rows && rows.length > 0) {
        items.push(...commandLogFromSummary(block.id, rows));
      }
    }
    return items;
  }, [summaries, systemLog]);

  const filteredLayers = useMemo(() => {
    const q = layerFilter.trim().toLowerCase();
    if (!q) return layers;
    return layers.filter(
      (l) => l.name.toLowerCase().includes(q) || l.source.toLowerCase().includes(q)
    );
  }, [layers, layerFilter]);

  const toggleLayer = (id: string) => {
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)));
  };

  const setAllLayers = (visible: boolean) => {
    setLayers((prev) => prev.map((l) => ({ ...l, visible })));
  };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-title">EdgeSense-130 Console (Read-Only)</div>
        <nav className="tabs" aria-label="Block views">
          {VIEWS.map((v) => (
            <button
              key={v.id}
              type="button"
              className={`tab ${selectedView === v.id ? "active" : ""}`}
              onClick={() => setSelectedView(v.id)}
            >
              {v.label}
            </button>
          ))}
        </nav>
        <div className="tabs">
          <button type="button" className="small-btn" onClick={() => setZoom((z) => Math.max(25, z - 25))}>
            -
          </button>
          <button type="button" className="small-btn" onClick={() => setZoom(100)}>
            {zoom}%
          </button>
          <button type="button" className="small-btn" onClick={() => setZoom((z) => Math.min(400, z + 25))}>
            +
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="pane left">
          <div className="pane-head">
            <span>Library Tree</span>
            <span>{ALL_BLOCKS.length} cells</span>
          </div>
          <div className="pane-body">
            {TRACKS.map((track) => (
              <div key={track.id} className="track-group">
                <div className="track-label">
                  <TrackIcon />
                  <span>{track.label}</span>
                </div>
                {track.blocks.map((block) => {
                  const st = blockStatus(summaries[block.id] ?? null);
                  return (
                    <button
                      key={block.id}
                      type="button"
                      className={`block-btn ${block.id === selectedBlock ? "active" : ""}`}
                      onClick={() => setSelectedBlock(block.id)}
                    >
                      <span className="block-name">
                        <BlockIcon />
                        <span>{block.id}</span>
                      </span>
                      <span className={`badge ${statusClass(st)}`}>{st}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </aside>

        <main
          className="canvas"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const scale = zoom / 100;
            setCursor({
              x: Number(((e.clientX - rect.left) / scale).toFixed(1)),
              y: Number(((e.clientY - rect.top) / scale).toFixed(1)),
            });
          }}
        >
          {selectedView === "results" ? (
            <section className="results-card">
              <div className="results-head">
                <div>
                  <strong>{currentBlock.id}</strong> : {currentBlock.role}
                </div>
                <span className={`badge ${statusClass(currentStatus)}`}>{currentStatus}</span>
              </div>
              {!currentRows ? (
                <p>not run (no projects/{currentBlock.id}/results/summary.json found)</p>
              ) : (
                <table className="results-table">
                  <thead>
                    <tr>
                      <th>Check</th>
                      <th>Result</th>
                      <th>Time</th>
                      <th>Logs and SHA-256</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentRows.map((row) => (
                      <tr key={row.name}>
                        <td>{row.name}</td>
                        <td>
                          <span className={`badge ${row.result}`}>{row.result}</span>
                        </td>
                        <td>{row.time}</td>
                        <td>
                          {row.logs.map((log) => (
                            <div key={log.file} className="hash-line">
                              <span className="hash-file">{log.file}</span>
                              <span>{log.sha256}</span>
                            </div>
                          ))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          ) : (
            <section className="results-card">
              <div className="results-head">
                <strong>
                  {currentBlock.id} / {selectedView}
                </strong>
                <span className={`badge ${statusClass(currentStatus)}`}>{currentStatus}</span>
              </div>
              <p>
                Read-only v1 shell active for {currentBlock.id}. Results view is live; {selectedView} renderer connects once exported artifacts are logged in projects/{currentBlock.id}/results/.
              </p>
            </section>
          )}
        </main>

        <aside className="pane right">
          <div className="pane-head">
            <span>SG13G2 Layers ({filteredLayers.length})</span>
            <div className="tabs">
              <button type="button" className="small-btn" onClick={() => setAllLayers(true)}>
                All
              </button>
              <button type="button" className="small-btn" onClick={() => setAllLayers(false)}>
                None
              </button>
            </div>
          </div>
          <div className="pane-body">
            <input
              type="text"
              className="layer-search"
              placeholder="Filter layer or GDS..."
              value={layerFilter}
              onChange={(e) => setLayerFilter(e.target.value)}
            />
            {filteredLayers.map((layer) => (
              <div key={layer.id} className="layer-row" onClick={() => toggleLayer(layer.id)}>
                <EyeIcon open={layer.visible} />
                <span
                  className="swatch"
                  style={{
                    background: layer.visible ? layer.fillColor : "transparent",
                    borderColor: layer.frameColor,
                    opacity: layer.visible ? 0.85 : 0.35,
                  }}
                />
                <span>{layer.name}</span>
                <span className="layer-src">
                  {layer.source} {layer.dither}
                </span>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <section className="cmdlog">
        <div className="pane-head">
          <span>Command Log (Loaded Files and SHA-256)</span>
          <span>{commandLog.length} entries</span>
        </div>
        <div className="cmdlog-body">
          {commandLog.map((item) => (
            <div key={`${item.path}-${item.sha256}`} className="cmdlog-row">
              <span>{item.path}</span>
              <span className="cmdlog-sha">{item.sha256}</span>
              <span>{item.note}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="statusbar">
        <div className="status-group">
          <span>X: {cursor.x.toFixed(1)} um</span>
          <span>Y: {cursor.y.toFixed(1)} um</span>
          <span>Zoom: {zoom}%</span>
        </div>
        <div className="status-group">
          <span>Cell: {currentBlock.id}</span>
          <span>View: {selectedView}</span>
          <span>Status: {currentStatus}</span>
        </div>
      </footer>
    </div>
  );
}
