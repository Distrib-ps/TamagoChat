import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { PixelIcon, cx } from "../../components/ui.jsx";
import { api, quiet } from "../../lib/api.js";
import { describeItem, fmtDelay, hhmm } from "../../lib/format.js";
import { usePolling } from "../../lib/hooks.js";

const STATUS = {
  delivered: ["reçu", "bg-leaf"],
  fetched: ["envoyé", "bg-water"],
  waiting: ["en attente", "bg-paper-2"],
};

function Status({ it }) {
  const [label, color] = STATUS[it.delivered ? "delivered" : it.fetched ? "fetched" : "waiting"];
  return <span class="inline-flex items-center gap-1.5"><span class={cx("size-2 border border-line", color)} />{label}</span>;
}

const bubble = "max-w-[min(36rem,85%)] border-2 border-line px-3 py-2 [overflow-wrap:anywhere]";
const meta = "mt-1 flex flex-wrap gap-x-2 text-xs text-ink-soft";

function Message({ it, many, fresh }) {
  if (it.type === "reply") {
    return (
      <div class={cx("flex origin-bottom-left flex-col items-start", fresh && "animate-pop")}>
        <p class={cx(bubble, "rounded-2xl rounded-bl-sm bg-paper")}>{it.text}</p>
        <p class={meta}>{it.cat}, {hhmm(it.created)}</p>
      </div>
    );
  }
  if (it.kind === "say") {
    const details = [many && `pour ${it.cat}`, it.from && `signé ${it.from}`, it.secs && `bulle ${fmtDelay(it.secs)}`,
      hhmm(it.created)].filter(Boolean).join(", ");
    return (
      <div class={cx("flex origin-bottom-right flex-col items-end", fresh && "animate-pop")}>
        <p class={cx(bubble, "rounded-2xl rounded-br-sm bg-fur-soft")}>{it.text}</p>
        <p class={meta}><span>{details}</span><Status it={it} /></p>
      </div>
    );
  }
  const { icon, text } = describeItem(it);
  return (
    <p class={cx("flex flex-wrap items-center justify-center gap-x-2 gap-y-1 self-center text-center text-sm text-ink-soft",
      fresh && "animate-pop")}>
      <PixelIcon name={icon} />
      <span class="text-ink">{text}</span>
      {many && <span>pour {it.cat}</span>}
      <Status it={it} />
    </p>
  );
}

// `version` change après chaque envoi : le fil est rechargé tout de suite
export function Feed({ selected, version }) {
  const [items, setItems] = useState(null);
  const box = useRef(null);
  const stick = useRef(true);          // reste collé en bas tant qu'on n'a pas remonté le fil
  const seen = useRef(null);           // messages déjà affichés : seuls les nouveaux apparaissent en animation
  const current = useRef(selected);
  current.current = selected;

  usePolling(() => {
    const cat = selected;
    api("/admin/api/feed?cat=" + encodeURIComponent(cat))
      .then((r) => { if (current.current === cat) setItems(r.items); })
      .catch(quiet);
  }, 3000, [selected, version]);

  useLayoutEffect(() => { setItems(null); stick.current = true; seen.current = null; }, [selected]);
  useLayoutEffect(() => {
    if (stick.current && box.current) box.current.scrollTop = box.current.scrollHeight;
    if (items) seen.current = new Set(items.map((it) => it.type + it.id));
  }, [items]);
  const onScroll = () => {
    const f = box.current;
    stick.current = f.scrollHeight - f.scrollTop - f.clientHeight < 80;
  };

  return (
    <div ref={box} onScroll={onScroll} class="flex min-h-0 flex-1 flex-col gap-3.5 overflow-y-auto bg-paper-2 px-3 py-4 md:px-5 md:py-5">
      {items && !items.length && (
        <p class="m-auto text-center text-ink-soft">Pas encore de messages. Écris-lui un mot ou envoie-lui une bêtise.</p>
      )}
      {items && items.map((it) => (
        <Message key={it.type + it.id} it={it} many={selected === "*"} fresh={seen.current && !seen.current.has(it.type + it.id)} />
      ))}
    </div>
  );
}
