import { useEffect, useRef, useState } from "preact/hooks";
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
    <div class="card">
      <h3>🏷️ Nom du chat</h3>
      <div class="body">
        <div class="namebox">
          <input ref={input} type="text" maxlength={24} placeholder="Nouveau nom" value={draft} disabled={disabled}
                 onInput={(e) => setDraft(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === "Enter") rename(); }} />
          <button class="btn small" onClick={rename} disabled={disabled}>Renommer</button>
          <PendingMark p={pending} />
        </div>
        <div class="hint">Il annoncera lui-même son nouveau nom.</div>
      </div>
    </div>
  );
}
