import { useRef, useState } from "preact/hooks";
import { Button, control, cx } from "../../components/ui.jsx";
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
    <form ref={form} onSubmit={submit} class="flex shrink-0 flex-col gap-2 border-t-2 border-line px-3 py-2.5 md:gap-2.5 md:px-5 md:py-3.5">
      <div class="flex gap-2">
        <textarea ref={area} maxlength={500} rows={2} aria-label="Message" enterkeyhint="send"
                  placeholder="Écris un message pour sa bulle"
                  class={cx(control, "min-w-0 flex-1 resize-none")}
                  value={text} onInput={(e) => setText(e.currentTarget.value)} onKeyDown={onKey} />
        <Button variant="primary" type="submit" disabled={busy}>Envoyer</Button>
      </div>
      <div class="flex items-center gap-x-2 text-sm text-ink-soft md:gap-x-3">
        <label for="from" class="sr-only">Signé par</label>
        <input id="from" maxlength={40} placeholder="Signé par" value={from} onInput={changeFrom}
               class={cx(control, "w-0 min-w-0 flex-1 px-2 py-1 sm:w-48 sm:flex-none")} />
        <label for="secs">Bulle</label>
        <select id="secs" value={secs} onChange={(e) => setSecs(e.currentTarget.value)} class={cx(control, "px-2 py-1")}>
          {BUBBLE_SECS.map(([v, label]) => <option value={v}>{label}</option>)}
        </select>
        <span class="ml-auto hidden lg:inline">Ctrl + Entrée pour envoyer</span>
      </div>
    </form>
  );
}
