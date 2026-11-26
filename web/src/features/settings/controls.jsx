import { control, cx } from "../../components/ui.jsx";
import { fmtDelay } from "../../lib/format.js";

export const LATE_MS = 30000;    // au-delà, le chat n'a sans doute pas reçu le changement

export function PendingMark({ p }) {
  if (!p) return <span />;
  const late = Date.now() - p.t > LATE_MS;
  return (
    <span class={cx("whitespace-nowrap rounded-full border-2 border-line px-2 text-xs", late ? "bg-warn" : "bg-paper-2")}
          title={late ? "Pas encore appliqué (chat hors ligne ?)" : "Envoyé, en attente du chat"}>
      {late ? "pas appliqué" : "envoi…"}
    </span>
  );
}

// stack : sur téléphone, le contrôle passe sous le libellé (menus déroulants trop larges pour tenir à côté)
export const Field = ({ label, hint, pending, stack, children }) => (
  <div class={cx("grid items-center gap-x-3 gap-y-1.5 sm:grid-cols-[1fr_auto_5.5rem]", stack ? "grid-cols-1" : "grid-cols-[1fr_auto]")}>
    <div>
      <div class="font-bold">{label}</div>
      {hint && <div class="text-sm text-ink-soft">{hint}</div>}
    </div>
    {children}
    {pending && <span class={cx("sm:col-span-1", !stack && "col-span-2")}><PendingMark p={pending} /></span>}
  </div>
);

export const Switch = ({ value, onChange, disabled, label }) => (
  <label class="relative inline-flex">
    <input type="checkbox" class="peer sr-only" checked={!!value} disabled={disabled} aria-label={label}
           onChange={(e) => onChange(e.currentTarget.checked)} />
    <span class={cx(
      "h-7 w-12 rounded-full border-2 border-line bg-paper-2 transition-colors peer-checked:bg-leaf",
      "peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-water peer-disabled:opacity-50",
      "after:absolute after:left-1 after:top-1 after:size-5 after:rounded-full after:border-2 after:border-line after:bg-paper",
      "after:transition-transform peer-checked:after:translate-x-5 motion-reduce:after:transition-none",
    )} />
  </label>
);

export function PresetSelect({ value, presets, unit, onChange, disabled, label }) {
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
    <select value={String(value)} onChange={change} disabled={disabled} aria-label={label} class={cx(control, "w-full py-1.5 sm:w-auto")}>
      {presets.map(([v, text]) => <option value={String(v)}>{text}</option>)}
      {custom && <option value={String(value)}>Personnalisé ({unit === "s" ? fmtDelay(value) : value + " min"})</option>}
      <option value="custom">Autre…</option>
    </select>
  );
}
