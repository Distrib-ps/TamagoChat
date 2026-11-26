import { Fragment } from "preact";
import { STATES, STATS } from "../../constants.js";
import { api } from "../../lib/api.js";
import { ago } from "../../lib/format.js";

export function CatHeader({ cat, now, onForgotten }) {
  if (!cat) {
    return (
      <div class="cathead">
        <div class="left">
          <h2>Tous les chats</h2>
          <div class="meta">Ce que tu envoies ici part vers chaque chat connu.</div>
        </div>
      </div>
    );
  }
  const forget = async () => {
    if (!confirm(`Retirer ${cat.name} de la liste ? (il réapparaîtra s'il se reconnecte)`)) return;
    await api("/admin/api/forget", { cat: cat.id });
    onForgotten();
  };
  const state = cat.online
    ? `🟢 En ligne · ${STATES[cat.state] || cat.state || ""}`
    : `⚪ Hors ligne · vu ${ago(cat.last_seen, now)}`;
  return (
    <div class="cathead">
      <div class="left">
        <h2>{cat.name}</h2>
        <div class="meta">{state}</div>
        <div class="meta">Version {cat.version || "?"}{cat.accept ? "" : " · messages désactivés de son côté"}</div>
        <button class="linkbtn" onClick={forget}>Oublier ce chat</button>
      </div>
      <div class="stats">
        {STATS.map(([k, label]) => {
          const v = cat.stats[k] ?? 0;
          return (
            <Fragment key={k}>
              <span>{label}</span>
              <div class="bar"><i style={{ width: v + "%", background: `var(--s-${k})` }} /></div>
              <span class="v">{Math.round(v)}</span>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
