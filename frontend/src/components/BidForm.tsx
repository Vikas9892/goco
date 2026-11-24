import { useState, type FormEvent } from "react";
import { api, type RfqDetail } from "../api";
import { money } from "../format";

const inDays = (n: number) => new Date(Date.now() + n * 86_400_000).toISOString().slice(0, 10);

export function BidForm({ rfq, onPlaced }: { rfq: RfqDetail; onPlaced: (detail: RfqDetail) => void }) {
  const [form, setForm] = useState({
    carrier_name: "", freight_charges: "", origin_charges: "0", destination_charges: "0",
    transit_days: "20", quote_valid_until: inDays(30),
  });
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const total = ["freight_charges", "origin_charges", "destination_charges"]
    .reduce((sum, k) => sum + (Number(form[k as keyof typeof form]) || 0), 0);
  const leader = rfq.ranking[0];
  const own = rfq.ranking.find((b) => b.carrier_name === form.carrier_name.trim());

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      onPlaced(await api.placeBid(rfq.id, { ...form, transit_days: Number(form.transit_days) }));
      setForm((f) => ({ ...f, freight_charges: "" }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card bid-form" onSubmit={submit}>
      <h2>Submit quote</h2>
      <label>Carrier name<input required value={form.carrier_name} onChange={set("carrier_name")} list="carriers" /></label>
      <datalist id="carriers">{rfq.ranking.map((b) => <option key={b.id} value={b.carrier_name} />)}</datalist>
      <div className="row">
        <label>Freight<input required type="number" min="0.01" step="0.01" value={form.freight_charges} onChange={set("freight_charges")} /></label>
        <label>Origin<input type="number" min="0" step="0.01" value={form.origin_charges} onChange={set("origin_charges")} /></label>
        <label>Destination<input type="number" min="0" step="0.01" value={form.destination_charges} onChange={set("destination_charges")} /></label>
      </div>
      <div className="row">
        <label>Transit (days)<input required type="number" min="1" max="365" value={form.transit_days} onChange={set("transit_days")} /></label>
        <label>Quote valid until<input required type="date" min={inDays(0)} value={form.quote_valid_until} onChange={set("quote_valid_until")} /></label>
      </div>
      <p className="hint">
        Total <strong>{money(String(total))}</strong>
        {leader && <> · L1 is {money(leader.total_amount)}</>}
        {own && <> · your best is {money(own.total_amount)} (L{own.rank})</>}
      </p>
      {error && <p className="error" role="alert">{error}</p>}
      <button disabled={busy}>{busy ? "Submitting…" : "Place bid"}</button>
    </form>
  );
}
