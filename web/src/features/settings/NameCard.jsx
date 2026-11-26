import { useEffect, useRef, useState } from "preact/hooks";
import { Button, Panel, PanelTitle, control, cx } from "../../components/ui.jsx";
import { PendingMark } from "./controls.jsx";

export function NameCard({ name, pending, onRename, disabled }) {
  const [draft, setDraft] = useState(name);
  const input = useRef(null);
  useEffect(() => { if (document.activeElement !== input.current) setDraft(name); }, [name]);
  const rename = () => {
    const v = draft.trim();
    if (v && v !== name) onRename(v);
    input.current.blur();
  };
  return (
    <Panel class="grid content-start gap-3.5 p-4 md:p-5">
      <PanelTitle icon="rename">Nom du chat</PanelTitle>
      <div class="flex flex-wrap items-center gap-2.5">
        <input ref={input} type="text" maxlength={24} placeholder="Nouveau nom" aria-label="Nom du chat" value={draft}
               disabled={disabled} class={cx(control, "min-w-0 flex-1")}
               onInput={(e) => setDraft(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === "Enter") rename(); }} />
        <Button variant="primary" size="sm" onClick={rename} disabled={disabled}>Renommer</Button>
        <PendingMark p={pending} />
      </div>
      <p class="text-sm text-ink-soft">Il annoncera lui-même son nouveau nom.</p>
    </Panel>
  );
}
