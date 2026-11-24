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

  const startDemo = () => api.startDemo().then((rfq) => navigate(`/rfqs/${rfq.id}`), (e: Error) => setError(e.message));

  return (
    <>
      <header className="page-header">
        <div>
          <h1>British Auctions</h1>
          <p className="muted">Live reverse auctions for freight RFQs. Late bids extend the clock, up to the forced close.</p>
        </div>
        <div className="actions">
          <button className="button-secondary" onClick={startDemo} title="Creates an auction that closes in 5 minutes">
            ▶ Start live demo
          </button>
          <Link to="/new" className="button">+ New RFQ</Link>
        </div>
      </header>
      {rfqs && (
        <section className="stats">
          {(["active", "scheduled", "closed", "force_closed"] as const).map((s) => (
            <div key={s} className="stat">
              <StatusBadge status={s} />
              <strong>{rfqs.filter((r) => r.status === s).length}</strong>
            </div>
          ))}
        </section>
      )}
      {error && <p className="error banner" role="alert">{error}</p>}
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
