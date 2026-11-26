import { useState } from "preact/hooks";
import { Button, Panel, PanelTitle } from "../../components/ui.jsx";
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
    <Panel class="grid gap-3.5 p-4 md:p-5">
      <PanelTitle icon="stats">Jauges</PanelTitle>
      {STATS.map(([k, label]) => (
        <label key={k} class="grid grid-cols-[5.5rem_minmax(0,1fr)_2rem] items-center gap-2 sm:grid-cols-[6.5rem_minmax(0,1fr)_2.5rem] sm:gap-3">
          <span class={k in moved ? "font-bold" : ""}>{label}</span>
          <input type="range" min={0} max={100} step={1} disabled={disabled} class="w-full min-w-0" style={{ "--gauge": `var(--color-${k})` }}
                 value={value(k)} onInput={(e) => setMoved({ ...moved, [k]: Number(e.currentTarget.value) })} />
          <span class="text-right tabular-nums">{value(k)}</span>
        </label>
      ))}
      <div class="flex flex-wrap items-center gap-2.5">
        <Button variant="primary" size="sm" disabled={disabled}
                onClick={() => apply(Object.fromEntries(STATS.map(([k]) => [k, value(k)])))}>Appliquer</Button>
        <Button size="sm" disabled={disabled}
                onClick={() => apply(Object.fromEntries(STATS.map(([k]) => [k, 100])))}>Tout à fond</Button>
        {sent && <span class="text-sm text-ink-soft">Envoi au chat…</span>}
      </div>
    </Panel>
  );
}
