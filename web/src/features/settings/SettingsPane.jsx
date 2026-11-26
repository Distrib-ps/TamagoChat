import { OldVersionNote, RemoteStatusNote } from "../cats/CatNotes.jsx";
import { BehaviorCard } from "./BehaviorCard.jsx";
import { GaugesCard } from "./GaugesCard.jsx";
import { NameCard } from "./NameCard.jsx";

// store : { settings: {clé: {v, t}}, stats } envoyés à ce chat, gardé d'un onglet à l'autre
export function SettingsPane({ cat, store, send }) {
  if (!cat.settings) return <OldVersionNote cat={cat} />;

  const pending = store.settings;
  const reported = (k) => (k === "name" ? cat.name : cat.settings[k]);
  for (const k of Object.keys(pending)) if (pending[k].v === reported(k)) delete pending[k];
  const value = (k) => (pending[k] ? pending[k].v : reported(k));
  const set = (changes) => {
    for (const [k, v] of Object.entries(changes)) pending[k] = { v, t: Date.now() };
    send({ kind: "settings", settings: changes });
  };
  const disabled = cat.allow_settings === false;

  return (
    <section class="grid min-h-0 flex-1 animate-fade grid-cols-[minmax(0,1fr)] content-start gap-4 overflow-y-auto bg-paper-2 p-3 md:gap-5 md:p-5">
      <RemoteStatusNote cat={cat} />
      <div class="grid grid-cols-[minmax(0,1fr)] gap-4 md:gap-5 xl:grid-cols-2">
        <NameCard name={value("name")} pending={pending.name} disabled={disabled} onRename={(v) => set({ name: v })} />
        <GaugesCard cat={cat} store={store} send={send} disabled={disabled} />
        <BehaviorCard value={value} pending={pending} set={set} disabled={disabled} />
      </div>
    </section>
  );
}
