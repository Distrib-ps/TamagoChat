import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { api, quiet } from "../../lib/api.js";
import { describeItem, fmtDelay, hhmm } from "../../lib/format.js";
import { usePolling } from "../../lib/hooks.js";

function Message({ it, many }) {
  if (it.type === "reply") {
    return (
      <div class="msg reply">
        <div class="b">{it.text}</div>
        <div class="m">{it.cat} · {hhmm(it.created)}</div>
      </div>
    );
  }
  const status = it.delivered ? "reçu ✓✓" : it.fetched ? "envoyé ✓" : "en attente…";
  const who = many ? `${it.cat} · ` : "";
  if (it.kind === "say") {
    const extra = (it.from ? "signé " + it.from + " · " : "") + (it.secs ? `bulle ${fmtDelay(it.secs)} · ` : "");
    return (
      <div class="msg sent">
        <div class="b">{it.text}</div>
        <div class="m">{who}{extra}{hhmm(it.created)} · {status}</div>
      </div>
    );
  }
  return (
    <div class="msg action">
      <div class="b">{describeItem(it)} · {who}{status}</div>
    </div>
  );
}

// `version` change après chaque envoi : le fil est rechargé tout de suite
export function Feed({ selected, version }) {
  const [items, setItems] = useState(null);
  const box = useRef(null);
  const stick = useRef(true);          // reste collé en bas tant qu'on n'a pas remonté le fil
  const current = useRef(selected);
  current.current = selected;

  usePolling(() => {
    const cat = selected;
    api("/admin/api/feed?cat=" + encodeURIComponent(cat))
      .then((r) => { if (current.current === cat) setItems(r.items); })
      .catch(quiet);
  }, 3000, [selected, version]);

  useLayoutEffect(() => { setItems(null); stick.current = true; }, [selected]);
  useLayoutEffect(() => {
    if (stick.current && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [items]);
  const onScroll = () => {
    const f = box.current;
    stick.current = f.scrollHeight - f.scrollTop - f.clientHeight < 80;
  };

  return (
    <div class="feed" ref={box} onScroll={onScroll}>
      {items && !items.length && <div class="feed-empty">Pas encore de messages. Dis bonjour ! 👋</div>}
      {items && items.map((it) => <Message key={it.type + it.id} it={it} many={selected === "*"} />)}
    </div>
  );
}
