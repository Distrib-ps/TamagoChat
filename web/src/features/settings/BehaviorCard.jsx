import { CHATTER, CRAZY, FLIES, SIZES } from "../../constants.js";
import { Field, PresetSelect, Segmented, Switch } from "./controls.jsx";

export function BehaviorCard({ value, pending, set, disabled }) {
  const select = (k, presets, unit) => (
    <PresetSelect value={value(k)} presets={presets} unit={unit} disabled={disabled} onChange={(v) => set({ [k]: v })} />
  );
  return (
    <div class="card">
      <h3>🐾 Comportement</h3>
      <div class="body">
        <Field label="Phrases spontanées" hint="Les réponses aux actions ne sont pas concernées." pending={pending.chatter_s}>
          {select("chatter_s", CHATTER, "s")}
        </Field>
        <Field label="Mode FOU" hint="Crises de folie automatiques." pending={pending.crazy_min}>
          {select("crazy_min", CRAZY, "min")}
        </Field>
        <Field label="Mouches" pending={pending.flies_min}>{select("flies_min", FLIES, "min")}</Field>
        <Field label="Se promène tout seul" pending={pending.autowalk}>
          <Switch value={value("autowalk")} disabled={disabled} onChange={(v) => set({ autowalk: v })} />
        </Field>
        <Field label="Toujours au premier plan" pending={pending.topmost}>
          <Switch value={value("topmost")} disabled={disabled} onChange={(v) => set({ topmost: v })} />
        </Field>
        <Field label="Taille" pending={pending.size}>
          <Segmented value={value("size")} values={SIZES} disabled={disabled} onChange={(v) => set({ size: v })} />
        </Field>
      </div>
    </div>
  );
}
