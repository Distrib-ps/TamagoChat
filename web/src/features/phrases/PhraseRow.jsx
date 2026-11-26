import { useState } from "preact/hooks";
import { IconButton, LinkButton, control, cx } from "../../components/ui.jsx";

const row = "flex items-center gap-2 border-t-2 border-line/15 px-3 py-1.5 first:border-t-0";

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
      <li class={row}>
        <input ref={(el) => el && el.focus()} value={draft} maxlength={200} aria-label="Phrase"
               class={cx(control, "min-w-0 flex-1 py-1")} onInput={(e) => setDraft(e.currentTarget.value)}
               onKeyDown={(e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") cancel(); }} />
        <LinkButton class="font-bold text-ink" onClick={commit}>Enregistrer</LinkButton>
        <LinkButton onClick={cancel}>Annuler</LinkButton>
      </li>
    );
  }
  return (
    <li class={row}>
      <span class="min-w-0 flex-1 [overflow-wrap:anywhere]">{text}</span>
      <IconButton icon="message" label="Lui faire dire maintenant" onClick={onSay} />
      <IconButton icon="rename" label="Modifier" disabled={disabled} onClick={() => { setDraft(text); setEditing(true); }} />
      <IconButton icon="quit" label="Supprimer" disabled={disabled} onClick={onDelete} />
    </li>
  );
}
