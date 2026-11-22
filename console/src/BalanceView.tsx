// Displays per-track hours and passing check counts with the 10% behind-leader balance rule.
import type { TrackBalance } from "./balance";

interface BalanceViewProps {
  rows: TrackBalance[];
}

export function BalanceView({ rows }: BalanceViewProps) {
  return (
    <section className="results-card">
      <div className="results-head">
        <strong>Track Balance (Digital / Analog / AMS)</strong>
        <span>Rule: no track more than 10% behind the leader</span>
      </div>
      <table className="results-table">
        <thead>
          <tr>
            <th>Track</th>
            <th>Logged Hours</th>
            <th>Passing Checks</th>
            <th>Hours Status</th>
            <th>Checks Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.track}>
              <td>{r.label}</td>
              <td>{r.hours.toFixed(1)} h</td>
              <td>{r.passedChecks}</td>
              <td>
                <span className={`badge ${r.behindHours ? "fail" : "pass"}`}>
                  {r.behindHours ? "behind >10%" : "ok"}
                </span>
              </td>
              <td>
                <span className={`badge ${r.behindChecks ? "fail" : "pass"}`}>
                  {r.behindChecks ? "behind >10%" : "ok"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
