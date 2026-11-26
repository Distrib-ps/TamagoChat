import { useEffect, useRef, useState } from "preact/hooks";
import { Note } from "../../components/Note.jsx";
import { Button, Panel, control, cx } from "../../components/ui.jsx";
import { toast } from "../../components/Toasts.jsx";
import { phraseLabels } from "../../constants.js";
import { api, quiet } from "../../lib/api.js";
import { plural } from "../../lib/format.js";
import { usePolling } from "../../lib/hooks.js";
import { OldVersionNote, RemoteStatusNote } from "../cats/CatNotes.jsx";
import { PhraseRow } from "./PhraseRow.jsx";

const LATE_MS = 30000;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
// le chat a-t-il appliqué cette modification ?
const applied = (data, k, loc) => (loc.reset ? !data.custom.includes(k) : same(data.list[k] || [], loc.list));

export function PhrasesPane({ cat, send }) {
  const [data, setData] = useState(null);        // phrases envoyées par le chat
  const [key, setKey] = useState(null);          // situation affichée
  const [local, setLocal] = useState({});        // modifications envoyées, pas encore confirmées
  const [editing, setEditing] = useState(-1);
  const [added, setAdded] = useState("");
  const at = useRef(undefined);

  usePolling(() => {
    if (!cat.settings) return;
    api("/admin/api/phrases?cat=" + encodeURIComponent(cat.id)).then((r) => {
      if (r.at === at.current) return;
      at.current = r.at;
      setData(r.phrases);
      for (const [k, label] of r.phrases?.cats || []) phraseLabels[k] = label;
    }).catch(quiet);
  }, 3000, [cat.id, !!cat.settings]);

  useEffect(() => {
    if (data) setLocal((l) => Object.fromEntries(Object.entries(l).filter(([k, loc]) => !applied(data, k, loc))));
  }, [data]);

  if (!cat.settings) return <OldVersionNote cat={cat} />;
  if (!data) {
    return (
      <section class="grid min-h-0 flex-1 animate-fade grid-cols-[minmax(0,1fr)] content-start gap-4 bg-paper-2 p-3 md:p-5">
        <RemoteStatusNote cat={cat} />
        <Note icon="sleep">{cat.name} n'a pas encore envoyé ses phrases : elles arrivent dès qu'il est en ligne.</Note>
      </section>
    );
  }

  const pending = Object.fromEntries(Object.entries(local).filter(([k, loc]) => !applied(data, k, loc)));
  const listOf = (k) => (pending[k] && !pending[k].reset ? pending[k].list : data.list?.[k] || []);
  const cur = key && data.cats.some((c) => c[0] === key) ? key : data.cats[0]?.[0];
  const list = listOf(cur);
  const loc = pending[cur];
  const custom = data.custom.includes(cur);
  const off = cat.allow_settings === false;

  const setList = (newList) => {
    setLocal({ ...local, [cur]: { list: newList, t: Date.now() } });
    setEditing(-1);
    send({ kind: "phrases", key: cur, list: newList });
  };
  const reset = () => {
    if (!confirm("Remettre les phrases d'origine pour cette situation ?")) return;
    setLocal({ ...local, [cur]: { reset: true, t: Date.now() } });
    send({ kind: "phrases", key: cur, reset: true });
  };
  const add = (e) => {
    e.preventDefault();
    const t = added.trim();
    if (!t) return;
    setList([...list, t]);
    setAdded("");
  };

  const status = loc && (Date.now() - loc.t > LATE_MS ? "pas encore appliqué" : "envoi au chat…");

  return (
    <section class="grid min-h-0 flex-1 animate-fade grid-cols-[minmax(0,1fr)] content-start gap-4 overflow-y-auto bg-paper-2 p-3 md:p-5">
      <RemoteStatusNote cat={cat} />
      <Panel class="grid gap-3 p-3 sm:p-4">
        <label class="grid gap-1.5">
          <span class="font-pixel">Situation</span>
          <select value={cur} disabled={off} class={cx(control, "w-full py-1.5")}
                  onChange={(e) => { setKey(e.currentTarget.value); setEditing(-1); }}>
            {data.cats.map(([k, label]) => (
              <option value={k}>{label} ({listOf(k).length}){data.custom.includes(k) ? ", personnalisées" : ""}</option>
            ))}
          </select>
        </label>
        <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <span class="text-sm text-ink-soft">
            {plural(list.length, "phrase")} {custom ? (list.length > 1 ? "personnalisées" : "personnalisée") : "d'origine"}{status && `, ${status}`}
          </span>
          {(custom || loc?.reset) && <Button size="sm" disabled={off} onClick={reset}>Rétablir l'origine</Button>}
        </div>
      </Panel>
      <Panel as="ul" class={cx("py-1", loc?.reset && "opacity-50")}>
        {!list.length && <li class="px-3 py-2 text-ink-soft">Aucune phrase : il ne dira rien dans cette situation.</li>}
        {list.map((text, i) => (
          <PhraseRow key={cur + i + text} text={text} disabled={off}
            editing={editing === i} setEditing={(on) => setEditing(on ? i : -1)}
            onSay={() => send({ kind: "say", text }).then((ok) => ok && toast("Envoyé"))}
            onSave={(v) => setList(list.map((x, j) => (j === i ? v : x)))}
            onDelete={() => setList(list.filter((_, j) => j !== i))} />
        ))}
      </Panel>
      <form onSubmit={add} class="flex gap-2">
        <input maxlength={200} placeholder="Nouvelle phrase" disabled={off} aria-label="Nouvelle phrase"
               class={cx(control, "min-w-0 flex-1")} value={added} onInput={(e) => setAdded(e.currentTarget.value)} />
        <Button variant="primary" type="submit" disabled={off}>Ajouter</Button>
      </form>
      <p class="text-sm text-ink-soft">
        Écris {"{name}"} pour glisser son nom dans une phrase. Chaque modification est envoyée au chat tout de suite.
      </p>
    </section>
  );
}
