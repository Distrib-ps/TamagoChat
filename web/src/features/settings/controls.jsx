import { fmtDelay } from "../../lib/format.js";

export const LATE_MS = 30000;    // au-delà, le chat n'a sans doute pas reçu le changement

export function PendingMark({ p }) {
  if (!p) return <span class="pend" />;
  const late = Date.now() - p.t > LATE_MS;
  return (
    <span class="pend" title={late ? "Pas encore appliqué (chat hors ligne ?)" : "Envoyé, en attente du chat…"}>
      {late ? "⚠️" : "⏳"}
    </span>
  );
}

export const Field = ({ label, hint, pending, children }) => (
  <div class="field">
    <div>
      <div>{label}</div>
      {hint && <div class="hint">{hint}</div>}
    </div>
    {children}
    <PendingMark p={pending} />
  </div>
);

export const Switch = ({ value, onChange, disabled }) => (
  <label class="switch">
    <input type="checkbox" checked={!!value} disabled={disabled} onChange={(e) => onChange(e.currentTarget.checked)} />
    <span />
  </label>
);

export const Segmented = ({ value, values, onChange, disabled }) => (
  <div class="seg">
    {values.map((v) => (
      <button type="button" key={v} class={v === value ? "on" : ""} disabled={disabled} onClick={() => onChange(v)}>{v}</button>
    ))}
  </div>
);

export function PresetSelect({ value, presets, unit, onChange, disabled }) {
  const custom = value != null && !presets.some((p) => p[0] === value);
  const change = (e) => {
    let v = e.currentTarget.value;
    if (v === "custom") {
      const ans = prompt(unit === "s" ? "Toutes les combien de minutes ? (0 = jamais)" : "Environ toutes les combien de minutes ? (0 = jamais)");
      const n = ans == null ? NaN : parseFloat(ans.replace(",", "."));
      if (!isFinite(n) || n < 0) { e.currentTarget.value = String(value); return; }
      v = unit === "s" ? (n === 0 ? 0 : Math.max(15, Math.min(86400, Math.round(n * 60)))) : Math.min(1440, Math.round(n));
    }
    onChange(Number(v));
  };
  return (
    <select value={String(value)} onChange={change} disabled={disabled}>
      {presets.map(([v, label]) => <option value={String(v)}>{label}</option>)}
      {custom && <option value={String(value)}>Personnalisé ({unit === "s" ? fmtDelay(value) : value + " min"})</option>}
      <option value="custom">Autre…</option>
    </select>
  );
}
