import { GaugeBar, LinkButton, PixelIcon, StatusDot } from "../../components/ui.jsx";
import { STAT_ICON, STATES, STATS } from "../../constants.js";
import { api } from "../../lib/api.js";
import { CAT_IMAGE } from "../../lib/assets.js";
import { ago } from "../../lib/format.js";

const Banner = ({ children }) => (
  <div class="flex flex-wrap items-center justify-between gap-3 border-b-2 border-line bg-fur px-3 py-3 text-line md:gap-5 md:px-5 md:py-4">
    {children}
  </div>
);

export function CatHeader({ cat, now, onForgotten }) {
  if (!cat) {
    return (
      <Banner>
        <div class="flex items-center gap-3 md:gap-3.5">
          <span key="all" class="animate-hop rounded-chip border-2 border-line bg-paper p-1.5 text-ink md:p-2">
            <PixelIcon name="paw" class="size-7 md:size-9" />
          </span>
          <div>
            <h2 class="font-pixel text-2xl font-bold md:text-3xl">Tous les chats</h2>
            <p class="text-sm md:text-base">Ce que tu envoies ici part vers chaque chat connu.</p>
          </div>
        </div>
      </Banner>
    );
  }
  const forget = async () => {
    if (!confirm(`Retirer ${cat.name} de la liste ? Il réapparaîtra s'il se reconnecte.`)) return;
    await api("/admin/api/forget", { cat: cat.id });
    onForgotten();
  };
  const state = cat.online
    ? `En ligne, ${STATES[cat.state] || cat.state || "tranquille"}`
    : `Hors ligne, vu ${ago(cat.last_seen, now)}`;
  return (
    <Banner>
      <div class="flex min-w-0 items-center gap-3 md:gap-3.5">
        <img key={cat.id} src={CAT_IMAGE} alt=""
             class="w-12 shrink-0 animate-hop rounded-chip border-2 border-line bg-paper p-1 [image-rendering:pixelated] md:w-16" />
        <div class="min-w-0">
          <h2 class="truncate font-pixel text-2xl font-bold md:text-3xl">{cat.name}</h2>
          <p class="flex items-center gap-2 text-sm md:text-base"><StatusDot on={cat.online} />{state}</p>
          <p class="text-xs md:text-sm">
            Version {cat.version || "?"}{cat.accept ? "" : ", messages désactivés de son côté"}
            <LinkButton class="ml-3 text-xs text-line/70 hover:text-line md:text-sm" onClick={forget}>Oublier ce chat</LinkButton>
          </p>
        </div>
      </div>
      <dl class="grid w-full grid-cols-4 gap-x-2.5 gap-y-2 rounded-chip border-2 border-line bg-paper px-2.5 py-2 text-ink sm:grid-cols-2 sm:gap-x-4 sm:px-3 md:w-96 md:px-3.5 md:py-2.5">
        {STATS.map(([k, label]) => {
          const v = cat.stats[k] ?? 0;
          return (
            <div key={k} title={label}>
              <div class="flex items-center justify-between gap-1 text-xs md:text-sm">
                <dt class="flex items-center gap-1">
                  <PixelIcon name={STAT_ICON[k]} class="size-3.5 sm:hidden" />
                  <span class="sr-only sm:not-sr-only">{label}</span>
                </dt>
                <dd class="tabular-nums">{Math.round(v)}</dd>
              </div>
              <GaugeBar stat={k} value={v} class="mt-0.5 h-2.5 md:h-3" />
            </div>
          );
        })}
      </dl>
    </Banner>
  );
}
