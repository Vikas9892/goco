// Types mirror backend/app/schemas.py. Money arrives as decimal strings to avoid float rounding.

export type Status = "scheduled" | "active" | "closed" | "force_closed";
export type TriggerType = "bid_received" | "any_rank_change" | "l1_change";

export interface RfqSummary {
  id: number;
  reference_id: string;
  name: string;
  status: Status;
  lowest_bid: string | null;
  bid_count: number;
  bid_start_at: string;
  bid_close_at: string;
  forced_close_at: string;
}

export interface RankedBid {
  rank: number;
  id: number;
  carrier_name: string;
  freight_charges: string;
  origin_charges: string;
  destination_charges: string;
  total_amount: string;
  transit_days: number;
  quote_valid_until: string;
  created_at: string;
}

export interface AuctionEvent {
  id: number;
  kind: "rfq_created" | "bid_placed" | "time_extended";
  message: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface RfqDetail {
  id: number;
  reference_id: string;
  name: string;
  pickup_date: string;
  status: Status;
  bid_start_at: string;
  original_close_at: string;
  bid_close_at: string;
  forced_close_at: string;
  config: { trigger_window_minutes: number; extension_minutes: number; trigger_type: TriggerType };
  ranking: RankedBid[];
  events: AuctionEvent[];
  stats: {
    bid_count: number;
    supplier_count: number;
    extension_count: number;
    opening_price: string | null;
    current_price: string | null;
    savings_percent: number | null;
  };
  server_time: string;
}

export interface BidInput {
  carrier_name: string;
  freight_charges: string;
  origin_charges: string;
  destination_charges: string;
  transit_days: number;
  quote_valid_until: string;
}

export type RfqInput = Omit<RfqDetail, "id" | "status" | "original_close_at" | "config" | "ranking" | "events" | "stats" | "server_time"> &
  RfqDetail["config"];

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // A 5xx with no JSON body means the API never answered (e.g. dev proxy can't reach :8000).
    const fallback = res.status >= 500 ? "Can't reach the auction server. Is the backend running?" : `Request failed (${res.status})`;
    throw new Error(errorMessage(body) ?? fallback);
  }
  return body as T;
}

// FastAPI sends either {detail: "msg"} (business rules) or {detail: [{msg}]} (validation).
function errorMessage(body: any): string | undefined {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => String(d.msg).replace(/^Value error, /, "")).join(". ");
}

export const api = {
  listRfqs: () => request<RfqSummary[]>("/rfqs"),
  getRfq: (id: number) => request<RfqDetail>(`/rfqs/${id}`),
  startDemo: () => request<RfqDetail>("/demo", { method: "POST" }),
  createRfq: (input: RfqInput) => request<RfqDetail>("/rfqs", { method: "POST", body: JSON.stringify(input) }),
  placeBid: (id: number, input: BidInput) =>
    request<RfqDetail>(`/rfqs/${id}/bids`, { method: "POST", body: JSON.stringify(input) }),
  liveUrl: (id: number) => `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/rfqs/${id}/live`,
};
