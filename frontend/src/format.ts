import type { Status, TriggerType } from "./api";

const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const dateTime = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });
const time = new Intl.DateTimeFormat(undefined, { timeStyle: "medium" });

export const money = (v: string | null) => (v === null ? "—" : inr.format(Number(v)));
export const when = (iso: string) => dateTime.format(new Date(iso));
export const clock = (iso: string) => time.format(new Date(iso));

export function duration(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const [d, h, m, sec] = [Math.floor(s / 86400), Math.floor(s / 3600) % 24, Math.floor(s / 60) % 60, s % 60];
  const pad = (n: number) => String(n).padStart(2, "0");
  return d ? `${d}d ${h}h ${pad(m)}m` : h ? `${h}:${pad(m)}:${pad(sec)}` : `${pad(m)}:${pad(sec)}`;
}

export const STATUS_LABEL: Record<Status, string> = {
  scheduled: "Scheduled",
  active: "Active",
  closed: "Closed",
  force_closed: "Force Closed",
};

export const TRIGGER_LABEL: Record<TriggerType, string> = {
  bid_received: "Any bid received",
  any_rank_change: "Any supplier rank change",
  l1_change: "Lowest bidder (L1) change",
};
