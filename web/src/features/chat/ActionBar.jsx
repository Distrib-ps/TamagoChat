import { useState } from "preact/hooks";
import { Button, PixelIcon, cx } from "../../components/ui.jsx";
import { ACTION_GROUPS } from "../../constants.js";

function ActionButton({ action, label, icon, send }) {
  const [hops, setHops] = useState(0);
  const click = async () => {
    if (await send({ kind: "action", action })) setHops((n) => n + 1);
  };
  return (
    <Button size="sm" onClick={click}>
      <span key={hops} class={hops ? "animate-hop" : ""}><PixelIcon name={icon} /></span>
      {label}
    </Button>
  );
}

// Sur téléphone, les actions sont dans un tiroir pour laisser la place à la conversation.
export function ActionBar({ send }) {
  const [open, setOpen] = useState(false);
  return (
    <div class="border-b-2 border-dashed border-ink-soft/40">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}
              class="flex w-full items-center gap-2 px-3 py-2.5 font-pixel md:hidden">
        <PixelIcon name="star" />
        Actions
        <span class="ml-auto font-sans text-sm text-ink-soft">{open ? "Masquer" : "Afficher"}</span>
      </button>
      <div class={cx(open ? "grid animate-drop" : "hidden",
        "max-h-[45dvh] gap-2.5 overflow-y-auto px-3 pb-3 md:grid md:max-h-none md:animate-none md:px-5 md:py-3.5")}>
        {ACTION_GROUPS.map(([title, list]) => (
          <div key={title} class="grid gap-1.5 sm:grid-cols-[5.5rem_1fr] sm:items-start">
            <h4 class="font-pixel text-sm text-ink-soft sm:mt-1.5">{title}</h4>
            <div class="flex flex-wrap gap-1.5">
              {list.map(([key, label, icon]) => <ActionButton key={key} action={key} label={label} icon={icon} send={send} />)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
