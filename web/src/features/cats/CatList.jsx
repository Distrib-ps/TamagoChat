import { useState } from "preact/hooks";
import { Dialog } from "../../components/Dialog.jsx";
import { GaugeBar, PixelIcon, Segmented, StatusDot, control, cx } from "../../components/ui.jsx";
import { STATES, STATS } from "../../constants.js";
import { ago, plural } from "../../lib/format.js";

const SEARCH_FROM = 6;    // en dessous, la liste se lit d'un coup d'œil

const item = (selected) => cx(
  "flex w-full flex-col gap-0.5 rounded-chip border-2 px-2.5 py-2 text-left",
  selected ? "border-line bg-fur-soft" : "border-transparent hover:bg-paper-2",
);

const Unread = ({ n }) => n > 0 && (
  <span class="rounded-full border-2 border-line bg-rose px-1.5 text-xs font-bold text-white">{n}</span>
);

function CatItem({ cat, selected, now, onSelect }) {
  const sub = cat.online ? (STATES[cat.state] || cat.state || "en ligne") : `vu ${ago(cat.last_seen, now)}`;
  return (
    <button class={item(selected)} aria-current={selected ? "true" : undefined} onClick={() => onSelect(cat.id)}>
      <span class="flex w-full items-center gap-2">
        <StatusDot on={cat.online} />
        <span class={cx("truncate font-pixel text-base font-bold", !cat.online && "text-ink-soft")}>{cat.name}</span>
        <Unread n={cat.unread} />
        <span class="ml-auto shrink-0 text-xs text-ink-soft">v{cat.version || "?"}</span>
      </span>
      <span class="flex w-full items-center gap-3">
        <span class="min-w-0 flex-1 truncate text-sm text-ink-soft">{sub}</span>
        <span class="grid w-20 shrink-0 grid-cols-4 gap-0.5" aria-hidden="true">
          {STATS.map(([k]) => <GaugeBar key={k} stat={k} value={cat.stats[k] ?? 0} thin class="h-2" />)}
        </span>
      </span>
    </button>
  );
}

// Recherche, filtre et liste : dans la colonne (ordinateur) comme dans le sélecteur (téléphone).
function CatBrowser({ cats, selected, now, onSelect }) {
  const [query, setQuery] = useState("");
  const [only, setOnly] = useState("all");
  const online = cats.filter((c) => c.online).length;
  const q = query.trim().toLowerCase();
  const shown = cats.filter((c) => (only === "all" || c.online) && (!q || c.name.toLowerCase().includes(q)));
  const tools = cats.length >= SEARCH_FROM;

  return (
    <div class="flex min-h-0 flex-1 flex-col gap-2">
      {tools && (
        <div class="grid gap-2">
          <input type="search" placeholder="Chercher un chat" aria-label="Chercher un chat" value={query}
                 class={cx(control, "py-1.5")} onInput={(e) => setQuery(e.currentTarget.value)} />
          <Segmented value={only} onChange={setOnly} class="w-full"
                     options={[["all", `Tous (${cats.length})`], ["online", `En ligne (${online})`]]} />
        </div>
      )}
      <button class={item(selected === "*")} aria-current={selected === "*" ? "true" : undefined} onClick={() => onSelect("*")}>
        <span class="flex items-center gap-2 font-pixel text-base font-bold"><PixelIcon name="paw" />Tous les chats</span>
        <span class="text-sm text-ink-soft">Un message ou une action pour tout le monde</span>
      </button>
      <div class="-mx-1 grid min-h-0 flex-1 content-start gap-1 overflow-y-auto px-1 border-t-2 border-dashed border-ink-soft/40 pt-2">
        {!cats.length && (
          <p class="p-2.5 text-sm text-ink-soft">Aucun chat pour l'instant. Ils apparaissent ici dès que quelqu'un lance TamagoChat.</p>
        )}
        {cats.length > 0 && !shown.length && (
          <p class="p-2.5 text-sm text-ink-soft">
            {q ? `Aucun chat ne s'appelle « ${query.trim()} ».` : "Aucun chat en ligne pour le moment."}
          </p>
        )}
        {shown.map((c) => <CatItem key={c.id} cat={c} selected={selected === c.id} now={now} onSelect={onSelect} />)}
      </div>
    </div>
  );
}

export const CatSidebar = (props) => (
  <aside class="hidden min-h-0 w-72 shrink-0 flex-col rounded-panel border-2 border-line bg-paper p-2 shadow-sticker lg:flex">
    <CatBrowser {...props} />
  </aside>
);

// Téléphone et tablette : le chat choisi, et un bouton pour en changer.
export function CatPicker({ cats, selected, now, onSelect }) {
  const [open, setOpen] = useState(false);
  const cat = cats.find((c) => c.id === selected);
  const unread = cats.reduce((n, c) => n + (c.id === selected ? 0 : c.unread || 0), 0);
  const choose = (id) => { onSelect(id); setOpen(false); };
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-haspopup="dialog"
        class="flex w-full shrink-0 items-center gap-2.5 rounded-chip border-2 border-line bg-paper px-3 py-2 text-left shadow-sticker-sm active:translate-0.5 active:shadow-none lg:hidden">
        {cat ? <StatusDot on={cat.online} /> : <PixelIcon name="paw" />}
        <span class="min-w-0 truncate font-pixel text-base font-bold">{cat ? cat.name : "Tous les chats"}</span>
        <span class="ml-auto flex shrink-0 items-center gap-2 text-sm text-ink-soft">
          <Unread n={unread} />
          <span class="hidden min-[360px]:inline">{plural(cats.length, "chat")}</span>
          <span class="font-bold text-ink underline underline-offset-2">Changer</span>
        </span>
      </button>
      <Dialog open={open} onClose={() => setOpen(false)} title="Choisir un chat" icon="paw" tall>
        <div class="flex min-h-0 flex-1 flex-col p-3 sm:p-4">
          <CatBrowser cats={cats} selected={selected} now={now} onSelect={choose} />
        </div>
      </Dialog>
    </>
  );
}
