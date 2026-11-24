import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type RfqSummary } from "../api";
import { StatusBadge } from "../components/StatusBadge";
import { duration, money, when } from "../format";
import { useNow, usePolling } from "../hooks";

export function AuctionList() {
  const [rfqs, setRfqs] = useState<RfqSummary[]>();
  const [error, setError] = useState<string>();
  const navigate = useNavigate();
  const now = useNow();

  // shortcut: polls every 5s; a list-wide WebSocket channel would be the upgrade if auctions number in the thousands.
  const load = useCallback(() => api.listRfqs().then(setRfqs, (e: Error) => setError(e.message)), []);
  usePolling(load, 5000);

  return (
    <>
      <header className="page-header">
        <h1>British Auctions</h1>
        <Link to="/new" className="button">+ New RFQ</Link>
      </header>
      {error && <p className="error">{error}</p>}
      {rfqs?.length === 0 && <p className="muted">No auctions yet. Create one, or run <code>python -m app.seed</code>.</p>}
      {!!rfqs?.length && (
        <div className="card table-scroll">
          <table>
            <thead>
              <tr><th>RFQ</th><th className="num">Lowest bid</th><th>Current close</th><th>Forced close</th><th>Status</th></tr>
            </thead>
            <tbody>
              {rfqs.map((r) => (
                <tr key={r.id} className="clickable" onClick={() => navigate(`/rfqs/${r.id}`)}>
                  <td>
                    <Link to={`/rfqs/${r.id}`}>{r.name}</Link>
                    <div className="muted mono">{r.reference_id} · {r.bid_count} bids</div>
                  </td>
                  <td className="num">{money(r.lowest_bid)}</td>
                  <td>
                    {when(r.bid_close_at)}
                    {r.status === "active" && <div className="muted mono">in {duration(new Date(r.bid_close_at).getTime() - now)}</div>}
                  </td>
                  <td>{when(r.forced_close_at)}</td>
                  <td><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
