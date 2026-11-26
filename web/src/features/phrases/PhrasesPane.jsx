import { useEffect, useRef, useState } from "preact/hooks";
import { Note } from "../../components/Note.jsx";
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
      <section class="pane">
        <RemoteStatusNote cat={cat} />
        <Note icon="⏳">{cat.name} n'a pas encore envoyé ses phrases : elles arrivent dès qu'il est en ligne.</Note>
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

  let info = `${plural(list.length, "phrase")} · ${custom ? "personnalisées ★" : "d'origine"}`;
  if (loc) info += Date.now() - loc.t > LATE_MS ? " · ⚠️ pas encore appliqué" : " · ⏳ envoi au chat…";

  return (
    <section class="pane">
      <RemoteStatusNote cat={cat} />
      <div class="ph-top">
        <select value={cur} disabled={off} onChange={(e) => { setKey(e.currentTarget.value); setEditing(-1); }}>
          {data.cats.map(([k, label]) => (
            <option value={k}>{data.custom.includes(k) ? "★ " : ""}{label} ({listOf(k).length})</option>
          ))}
        </select>
        <span class="ph-info">{info}</span>
        {(custom || loc?.reset) && (
          <button class="btn small ghost" disabled={off} onClick={reset}>↺ Rétablir l'origine</button>
        )}
      </div>
      <ul class={"ph-list" + (loc?.reset ? " stale" : "")}>
        {!list.length && <li class="empty">Aucune phrase : il ne dira rien dans cette situation.</li>}
        {list.map((text, i) => (
          <PhraseRow key={cur + i + text} text={text} disabled={off}
            editing={editing === i} setEditing={(on) => setEditing(on ? i : -1)}
            onSay={() => send({ kind: "say", text }).then((ok) => ok && toast("Envoyé !"))}
            onSave={(v) => setList(list.map((x, j) => (j === i ? v : x)))}
            onDelete={() => setList(list.filter((_, j) => j !== i))} />
        ))}
      </ul>
      <form class="ph-add" onSubmit={add}>
        <input maxlength={200} placeholder="Nouvelle phrase… (écris {name} pour son nom)" disabled={off}
               value={added} onInput={(e) => setAdded(e.currentTarget.value)} />
        <button class="btn small" disabled={off}>Ajouter</button>
      </form>
      <div class="hint">Chaque modification est envoyée au chat tout de suite. 💬 = la lui faire dire maintenant.</div>
    </section>
  );
}
