import { STATES, STATS } from "../../constants.js";
import { ago } from "../../lib/format.js";

function CatItem({ cat, selected, now, onSelect }) {
  const sub = cat.online ? (STATES[cat.state] || cat.state || "en ligne") : `vu ${ago(cat.last_seen, now)}`;
  return (
    <button class={"catitem" + (selected ? " sel" : "")} onClick={() => onSelect(cat.id)}>
      <div class="row">
        <span class={"dot" + (cat.online ? " on" : "")} />
        <span class="name">{cat.name}</span>
        {cat.unread > 0 && <span class="unread">{cat.unread}</span>}
      </div>
      <div class="sub">{sub} · v{cat.version || "?"}</div>
      <div class="minibars">
        {STATS.map(([k]) => (
          <span key={k}><i style={{ width: (cat.stats[k] ?? 0) + "%", background: `var(--s-${k})` }} /></span>
        ))}
      </div>
    </button>
  );
}

export function CatList({ cats, selected, now, onSelect }) {
  return (
    <aside>
      <button class={"catitem" + (selected === "*" ? " sel" : "")} onClick={() => onSelect("*")}>
        <div class="row"><span class="name">🐾 Tous les chats</span></div>
        <div class="sub">Message ou action pour tout le monde</div>
      </button>
      {!cats.length && (
        <div class="empty-side">Aucun chat pour l'instant. Ils apparaissent ici dès que quelqu'un lance TamagoChat.</div>
      )}
      {cats.map((c) => (
        <CatItem key={c.id} cat={c} selected={selected === c.id} now={now} onSelect={onSelect} />
      ))}
    </aside>
  );
}
