import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type TriggerType } from "../api";
import { TRIGGER_LABEL } from "../format";

// <input type="datetime-local"> works in local time without a zone; convert at the edges.
const toLocalInput = (ms: number) => new Date(ms - new Date().getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
const toIso = (local: string) => new Date(local).toISOString();
const MIN = 60_000;

export function CreateRfq() {
  const navigate = useNavigate();
  const now = Date.now();
  const [form, setForm] = useState({
    reference_id: `RFQ-${Math.floor(now / 1000) % 100000}`,
    name: "",
    pickup_date: toLocalInput(now + 3 * 86_400_000).slice(0, 10),
    bid_start_at: toLocalInput(now),
    bid_close_at: toLocalInput(now + 30 * MIN),
    forced_close_at: toLocalInput(now + 45 * MIN),
    trigger_window_minutes: "10",
    extension_minutes: "5",
    trigger_type: "bid_received" as TriggerType,
  });
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value });

  // Mirror the server rule instantly; the server still validates.
  const forcedTooEarly = form.forced_close_at <= form.bid_close_at;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(undefined);
    try {
      const rfq = await api.createRfq({
        ...form,
        bid_start_at: toIso(form.bid_start_at),
        bid_close_at: toIso(form.bid_close_at),
        forced_close_at: toIso(form.forced_close_at),
        trigger_window_minutes: Number(form.trigger_window_minutes),
        extension_minutes: Number(form.extension_minutes),
      });
      navigate(`/rfqs/${rfq.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <form className="card create-form" onSubmit={submit}>
      <h1>New RFQ · British Auction</h1>

      <fieldset>
        <legend>Shipment</legend>
        <div className="row">
          <label>Reference ID<input required maxLength={40} value={form.reference_id} onChange={set("reference_id")} /></label>
          <label>Pickup / service date<input required type="date" value={form.pickup_date} onChange={set("pickup_date")} /></label>
        </div>
        <label>RFQ name<input required maxLength={200} placeholder="e.g. Nhava Sheva → Rotterdam, 2×40' HC" value={form.name} onChange={set("name")} /></label>
      </fieldset>

      <fieldset>
        <legend>Bidding window</legend>
        <div className="row">
          <label>Bid start<input required type="datetime-local" value={form.bid_start_at} onChange={set("bid_start_at")} /></label>
          <label>Bid close<input required type="datetime-local" value={form.bid_close_at} onChange={set("bid_close_at")} /></label>
          <label>Forced close
            <input required type="datetime-local" value={form.forced_close_at} onChange={set("forced_close_at")} aria-invalid={forcedTooEarly} />
          </label>
        </div>
        {forcedTooEarly && <p className="error">Forced close must be later than bid close.</p>}
      </fieldset>

      <fieldset>
        <legend>Auto-extension</legend>
        <div className="row">
          <label>Trigger window X (min)<input required type="number" min="1" max="180" value={form.trigger_window_minutes} onChange={set("trigger_window_minutes")} /></label>
          <label>Extension Y (min)<input required type="number" min="1" max="180" value={form.extension_minutes} onChange={set("extension_minutes")} /></label>
          <label>Extend when
            <select value={form.trigger_type} onChange={set("trigger_type")}>
              {Object.entries(TRIGGER_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
        </div>
        <p className="hint">
          A qualifying bid in the last {form.trigger_window_minutes} min pushes the close out by {form.extension_minutes} min,
          never past the forced close.
        </p>
      </fieldset>

      {error && <p className="error" role="alert">{error}</p>}
      <button disabled={busy || forcedTooEarly}>{busy ? "Creating…" : "Create RFQ"}</button>
    </form>
  );
}
