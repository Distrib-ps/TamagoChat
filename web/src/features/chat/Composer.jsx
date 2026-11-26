import { useRef, useState } from "preact/hooks";
import { BUBBLE_SECS } from "../../constants.js";
import { readLocal, saveLocal } from "../../lib/hooks.js";

export function Composer({ send }) {
  const [text, setText] = useState("");
  const [from, setFrom] = useState(() => readLocal("minou_from", ""));
  const [secs, setSecs] = useState("");
  const [busy, setBusy] = useState(false);
  const area = useRef(null);
  const form = useRef(null);

  const submit = async (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    setBusy(true);
    const payload = { kind: "say", text: t, from: from.trim() };
    if (secs) payload.secs = Number(secs);
    if (await send(payload)) setText("");
    setBusy(false);
    area.current.focus();
  };
  const onKey = (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) form.current.requestSubmit();
  };
  const changeFrom = (e) => {
    setFrom(e.currentTarget.value);
    saveLocal("minou_from", e.currentTarget.value);
  };

  return (
    <form class="composer" ref={form} onSubmit={submit}>
      <textarea ref={area} maxlength={500} placeholder="Écris un message, il s'affichera dans la bulle du chat…"
                value={text} onInput={(e) => setText(e.currentTarget.value)} onKeyDown={onKey} />
      <button class="btn" type="submit" disabled={busy}>Envoyer</button>
      <div class="opts">
        <label for="from">Signé :</label>
        <input id="from" maxlength={40} placeholder="ton prénom (facultatif)" value={from} onInput={changeFrom} />
        <label for="secs">Bulle :</label>
        <select id="secs" value={secs} onChange={(e) => setSecs(e.currentTarget.value)}>
          {BUBBLE_SECS.map(([v, label]) => <option value={v}>{label}</option>)}
        </select>
        <span class="spacer" />
        <span>Ctrl + Entrée pour envoyer</span>
      </div>
    </form>
  );
}
