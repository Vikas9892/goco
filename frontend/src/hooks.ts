import { useCallback, useEffect, useState } from "react";
import { api, type RfqDetail } from "./api";

/** Current time, ticking every second, corrected by the server-vs-browser clock offset. */
export function useNow(offsetMs = 0): number {
  const [now, setNow] = useState(() => Date.now() + offsetMs);
  useEffect(() => {
    setNow(Date.now() + offsetMs);
    const id = setInterval(() => setNow(Date.now() + offsetMs), 1000);
    return () => clearInterval(id);
  }, [offsetMs]);
  return now;
}

/** Calls `fn` now and every `ms` milliseconds. */
export function usePolling(fn: () => void, ms: number) {
  useEffect(() => {
    fn();
    const id = setInterval(fn, ms);
    return () => clearInterval(id);
  }, [fn, ms]);
}

/**
 * Live auction state: fetched over REST, refreshed whenever the server pings over WebSocket
 * (another supplier bid) and when the auction crosses its start/close time.
 */
export function useLiveAuction(id: number) {
  const [rfq, setRfq] = useState<RfqDetail>();
  const [error, setError] = useState<string>();
  const [offsetMs, setOffsetMs] = useState(0);

  const apply = useCallback((detail: RfqDetail) => {
    setRfq(detail);
    setOffsetMs(new Date(detail.server_time).getTime() - Date.now());
  }, []);

  const refresh = useCallback(
    () => api.getRfq(id).then(apply, (e: Error) => setError(e.message)),
    [id, apply],
  );

  useEffect(() => {
    refresh();
    let ws: WebSocket;
    let retry: ReturnType<typeof setTimeout>;
    let closed = false;
    const connect = () => {
      ws = new WebSocket(api.liveUrl(id));
      ws.onmessage = refresh;
      ws.onclose = () => {
        if (!closed) retry = setTimeout(() => (refresh(), connect()), 2000); // catch up on anything missed
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(retry);
      ws.close();
    };
  }, [id, refresh]);

  // Status is time-based, so refetch the moment the next boundary passes.
  useEffect(() => {
    if (!rfq) return;
    const serverNow = Date.now() + offsetMs;
    const next = [rfq.bid_start_at, rfq.bid_close_at].map((t) => new Date(t).getTime()).find((t) => t > serverNow);
    if (next === undefined) return;
    const timer = setTimeout(refresh, Math.min(next - serverNow + 250, 2 ** 31 - 1)); // larger delays overflow and fire instantly
    return () => clearTimeout(timer);
  }, [rfq, offsetMs, refresh]);

  return { rfq, error, offsetMs, apply };
}
