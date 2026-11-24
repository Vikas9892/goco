import type { RfqDetail } from "../api";
import { clock } from "../format";

/**
 * The auction on one axis, start → forced close: how far the close has been pushed by extensions,
 * the live trigger window, and the headroom left before the hard stop.
 */
export function Timeline({ rfq, now }: { rfq: RfqDetail; now: number }) {
  const t = (iso: string) => new Date(iso).getTime();
  const start = t(rfq.bid_start_at);
  const span = t(rfq.forced_close_at) - start;
  const pct = (ms: number) => `${Math.min(100, Math.max(0, ((ms - start) / span) * 100))}%`;

  const close = t(rfq.bid_close_at);
  const windowStart = close - rfq.config.trigger_window_minutes * 60_000;

  return (
    <figure className="timeline" aria-label="Auction timeline">
      <div className="timeline-track">
        <div className="seg seg-base" style={{ left: 0, width: pct(t(rfq.original_close_at)) }} />
        <div className="seg seg-extended" style={{ left: pct(t(rfq.original_close_at)), right: `calc(100% - ${pct(close)})` }} />
        {rfq.status === "active" && <>
          <div className="seg seg-window" style={{ left: pct(windowStart), right: `calc(100% - ${pct(close)})` }} />
          <div className="now-marker" style={{ left: pct(now) }} title="Now" />
        </>}
      </div>
      <figcaption className="timeline-legend">
        <span>Start {clock(rfq.bid_start_at)}</span>
        <span><i className="dot dot-base" />Original close {clock(rfq.original_close_at)}</span>
        <span><i className="dot dot-extended" />Extended to {clock(rfq.bid_close_at)}</span>
        <span><i className="dot dot-window" />Trigger window ({rfq.config.trigger_window_minutes}m)</span>
        <span>Forced close {clock(rfq.forced_close_at)}</span>
      </figcaption>
    </figure>
  );
}
