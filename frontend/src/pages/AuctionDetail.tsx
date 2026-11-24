import { Link, useParams } from "react-router-dom";
import type { AuctionEvent, RfqDetail } from "../api";
import { BidForm } from "../components/BidForm";
import { StatusBadge } from "../components/StatusBadge";
import { Timeline } from "../components/Timeline";
import { clock, duration, money, TRIGGER_LABEL, when } from "../format";
import { useLiveAuction, useNow } from "../hooks";

export function AuctionDetail() {
  const id = Number(useParams().id);
  const { rfq, error, offsetMs, apply } = useLiveAuction(id);
  const now = useNow(offsetMs);

  if (error) return <p className="error">{error}</p>;
  if (!rfq) return <p className="muted">Loading…</p>;

  return (
    <>
      <Link to="/" className="back">← All auctions</Link>
      <header className="detail-header">
        <div>
          <p className="muted mono">{rfq.reference_id} · Pickup {rfq.pickup_date}</p>
          <h1>{rfq.name}</h1>
          <StatusBadge status={rfq.status} />
        </div>
        <Countdown rfq={rfq} now={now} />
      </header>

      <Timeline rfq={rfq} now={now} />
      <Stats stats={rfq.stats} />

      <div className="detail-grid">
        <div className="stack">
          <Ranking rfq={rfq} />
          <ActivityLog events={rfq.events} />
        </div>
        <aside className="stack">
          {rfq.status === "active" && <BidForm rfq={rfq} onPlaced={apply} />}
          <section className="card">
            <h2>Auction rules</h2>
            <dl className="config">
              <dt>Trigger window (X)</dt><dd>{rfq.config.trigger_window_minutes} min</dd>
              <dt>Extension (Y)</dt><dd>{rfq.config.extension_minutes} min</dd>
              <dt>Extends on</dt><dd>{TRIGGER_LABEL[rfq.config.trigger_type]}</dd>
              <dt>Forced close</dt><dd>{when(rfq.forced_close_at)}</dd>
            </dl>
          </section>
        </aside>
      </div>
    </>
  );
}

function Countdown({ rfq, now }: { rfq: RfqDetail; now: number }) {
  const close = new Date(rfq.bid_close_at).getTime();
  const inWindow = rfq.status === "active" && close - now <= rfq.config.trigger_window_minutes * 60_000;
  const [label, target] =
    rfq.status === "scheduled" ? ["Opens in", rfq.bid_start_at]
    : rfq.status === "active" ? ["Closes in", rfq.bid_close_at]
    : ["Ended", null];

  return (
    // Keyed on close time so the pulse animation replays whenever the auction is extended.
    <div key={rfq.bid_close_at} className={`countdown ${inWindow ? "countdown-hot" : ""}`}>
      <span className="muted">{label}</span>
      <strong className="mono">{target ? duration(new Date(target).getTime() - now) : clock(rfq.bid_close_at)}</strong>
      {inWindow && <span className="hot-note">Extension window: qualifying bids add {rfq.config.extension_minutes} min</span>}
    </div>
  );
}

function Stats({ stats }: { stats: RfqDetail["stats"] }) {
  const items = [
    ["Bids", stats.bid_count],
    ["Suppliers", stats.supplier_count],
    ["Extensions", stats.extension_count],
    ["Best price", money(stats.current_price)],
    ["Improvement vs opening bid", stats.savings_percent === null ? "—" : `${stats.savings_percent}%`],
  ];
  return (
    <section className="stats">
      {items.map(([label, value]) => (
        <div key={label} className="stat"><span className="muted">{label}</span><strong>{value}</strong></div>
      ))}
    </section>
  );
}

function Ranking({ rfq }: { rfq: RfqDetail }) {
  return (
    <section className="card">
      <h2>Supplier ranking</h2>
      {rfq.ranking.length === 0 ? <p className="muted">No bids yet.</p> : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr><th>Rank</th><th>Carrier</th><th className="num">Freight</th><th className="num">Origin</th>
                <th className="num">Destination</th><th className="num">Total</th><th>Transit</th><th>Valid until</th></tr>
            </thead>
            <tbody>
              {rfq.ranking.map((b) => (
                <tr key={b.id} className={b.rank === 1 ? "leader" : ""}>
                  <td><span className="rank">L{b.rank}</span></td>
                  <td>{b.carrier_name}</td>
                  <td className="num">{money(b.freight_charges)}</td>
                  <td className="num">{money(b.origin_charges)}</td>
                  <td className="num">{money(b.destination_charges)}</td>
                  <td className="num"><strong>{money(b.total_amount)}</strong></td>
                  <td>{b.transit_days} d</td>
                  <td>{b.quote_valid_until}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function ActivityLog({ events }: { events: AuctionEvent[] }) {
  return (
    <section className="card">
      <h2>Activity log</h2>
      <ol className="log">
        {events.map((e) => (
          <li key={e.id} className={`log-${e.kind}`}>
            <time className="mono muted">{clock(e.created_at)}</time>
            <span>{e.message}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
