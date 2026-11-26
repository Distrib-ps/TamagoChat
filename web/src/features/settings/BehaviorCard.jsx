import { Panel, PanelTitle, Segmented } from "../../components/ui.jsx";
import { CHATTER, CRAZY, FLIES, SIZES } from "../../constants.js";
import { Field, PresetSelect, Switch } from "./controls.jsx";

export function BehaviorCard({ value, pending, set, disabled }) {
  const select = (k, presets, unit, label) => (
    <PresetSelect value={value(k)} presets={presets} unit={unit} label={label} disabled={disabled}
                  onChange={(v) => set({ [k]: v })} />
  );
  return (
    <Panel class="grid gap-4 p-4 md:p-5 xl:col-span-2">
      <PanelTitle icon="paw">Comportement</PanelTitle>
      <Field stack label="Phrases spontanées" hint="Les réponses aux actions ne sont pas concernées." pending={pending.chatter_s}>
        {select("chatter_s", CHATTER, "s", "Phrases spontanées")}
      </Field>
      <Field stack label="Mode FOU" hint="Crises de folie automatiques." pending={pending.crazy_min}>
        {select("crazy_min", CRAZY, "min", "Mode FOU")}
      </Field>
      <Field stack label="Mouches" pending={pending.flies_min}>{select("flies_min", FLIES, "min", "Mouches")}</Field>
      <Field label="Se promène tout seul" pending={pending.autowalk}>
        <Switch label="Se promène tout seul" value={value("autowalk")} disabled={disabled} onChange={(v) => set({ autowalk: v })} />
      </Field>
      <Field label="Toujours au premier plan" pending={pending.topmost}>
        <Switch label="Toujours au premier plan" value={value("topmost")} disabled={disabled} onChange={(v) => set({ topmost: v })} />
      </Field>
      <Field stack label="Taille" pending={pending.size}>
        <Segmented value={value("size")} options={SIZES.map((s) => [s, s])} disabled={disabled} class="w-full sm:w-auto"
                   onChange={(v) => set({ size: v })} />
      </Field>
    </Panel>
  );
}
