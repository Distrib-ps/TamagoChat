import { useState } from "preact/hooks";

export function PhraseRow({ text, editing, setEditing, onSay, onSave, onDelete, disabled }) {
  const [draft, setDraft] = useState(text);
  if (editing) {
    const commit = () => {
      const v = draft.trim();
      setEditing(false);
      if (v && v !== text) onSave(v);
    };
    const cancel = () => setEditing(false);
    return (
      <li>
        <input ref={(el) => el && el.focus()} value={draft} maxlength={200} onInput={(e) => setDraft(e.currentTarget.value)}
               onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") cancel(); }} />
        <button class="ib" title="Enregistrer" onClick={commit}>✔️</button>
        <button class="ib" title="Annuler" onClick={cancel}>✖️</button>
      </li>
    );
  }
  return (
    <li>
      <span class="t">{text}</span>
      <button class="ib" title="Lui faire dire maintenant" onClick={onSay}>💬</button>
      <button class="ib" title="Modifier" disabled={disabled} onClick={() => { setDraft(text); setEditing(true); }}>✏️</button>
      <button class="ib" title="Supprimer" disabled={disabled} onClick={onDelete}>🗑️</button>
    </li>
  );
}
