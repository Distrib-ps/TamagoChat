import { useState } from "preact/hooks";
import { STATS } from "../../constants.js";
import { LATE_MS } from "./controls.jsx";

// store.stats : jauges envoyées, affichées jusqu'à ce que le chat les confirme (ou 30 s)
export function GaugesCard({ cat, store, send, disabled }) {
  const [moved, setMoved] = useState({});      // curseurs déplacés, pas encore appliqués
  let sent = store.stats;
  const confirmed = sent && STATS.every(([k]) => Math.abs((cat.stats[k] ?? -99) - sent.vals[k]) < 2);
  if (sent && (confirmed || Date.now() - sent.t > LATE_MS)) store.stats = sent = null;

  const value = (k) => moved[k] ?? Math.round(sent ? sent.vals[k] : (cat.stats[k] ?? 0));
  const apply = (vals) => {
    store.stats = { vals, t: Date.now() };
    setMoved({});
    send({ kind: "stats", stats: vals });
  };
  return (
    <div class="card">
      <h3>📊 Jauges</h3>
      <div class="body">
        {STATS.map(([k, label]) => (
          <div class={"gauge" + (k in moved ? " dirty" : "")} key={k}>
            <span>{label}</span>
            <input type="range" min={0} max={100} step={1} style={{ accentColor: `var(--s-${k})` }} disabled={disabled}
                   value={value(k)} onInput={(e) => setMoved({ ...moved, [k]: Number(e.currentTarget.value) })} />
            <span class="v">{value(k)}</span>
          </div>
        ))}
        <div class="row-btns">
          <button class="btn small" disabled={disabled}
                  onClick={() => apply(Object.fromEntries(STATS.map(([k]) => [k, value(k)])))}>Appliquer</button>
          <button class="btn small ghost" disabled={disabled}
                  onClick={() => apply(Object.fromEntries(STATS.map(([k]) => [k, 100])))}>💯 Tout à fond</button>
          <span class="hint">{sent ? "⏳ envoi…" : ""}</span>
        </div>
      </div>
    </div>
  );
}
