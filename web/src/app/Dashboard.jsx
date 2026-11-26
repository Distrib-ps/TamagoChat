import { useEffect, useRef, useState } from "preact/hooks";
import { toast } from "../components/Toasts.jsx";
import { CatHeader } from "../features/cats/CatHeader.jsx";
import { CatPicker, CatSidebar } from "../features/cats/CatList.jsx";
import { ChatPane } from "../features/chat/ChatPane.jsx";
import { DeployDialog } from "../features/deploy/DeployDialog.jsx";
import { PhrasesPane } from "../features/phrases/PhrasesPane.jsx";
import { SettingsPane } from "../features/settings/SettingsPane.jsx";
import { PixelIcon, cx } from "../components/ui.jsx";
import { AuthError, api } from "../lib/api.js";
import { Header } from "./Header.jsx";

const TABS = [["chat", "Messages et actions", "Messages", "message"], ["settings", "Réglages et jauges", "Réglages", "options"],
  ["phrases", "Phrases", "Phrases", "phrases"]];

export function Dashboard({ data, refresh, onLogout }) {
  const [selected, setSelected] = useState("*");        // id du chat, ou "*" pour tous
  const [tab, setTab] = useState("chat");
  const [deployOpen, setDeployOpen] = useState(false);
  const [feedVersion, setFeedVersion] = useState(0);     // recharge le fil après un envoi
  const pendingByCat = useRef({});                       // réglages et jauges envoyés, pas encore confirmés

  const cat = data.cats.find((c) => c.id === selected) || null;
  useEffect(() => { if (selected !== "*" && !cat) setSelected("*"); }, [selected, cat]);
  const current = cat ? tab : "chat";
  const store = cat ? (pendingByCat.current[cat.id] ||= { settings: {}, stats: null }) : null;

  const send = async (payload) => {
    try {
      const r = await api("/admin/api/send", { cat: selected, ...payload });
      if (!r.sent) toast("Aucun chat à qui l'envoyer.");
      else if (current !== "chat" && payload.kind === "action") toast("Envoyé !");
      setFeedVersion((v) => v + 1);
      return true;
    } catch (e) {
      if (!(e instanceof AuthError)) toast("Erreur : " + e.message);
      return false;
    }
  };

  return (
    <section class="flex h-dvh flex-col">
      <Header data={data} onDeploy={() => setDeployOpen(true)} onLogout={onLogout} />
      <DeployDialog open={deployOpen} onClose={() => setDeployOpen(false)} cats={data.cats} now={data.now} />
      {/* marge droite et basse plus large : elle compense l'ombre décalée des panneaux */}
      <div class="flex min-h-0 flex-1 flex-col gap-3 pr-4 pb-4 pl-3 sm:pr-5 sm:pl-4 lg:flex-row lg:gap-5 lg:pr-7 lg:pb-7 lg:pl-6">
        <CatSidebar cats={data.cats} selected={selected} now={data.now} onSelect={setSelected} />
        <CatPicker cats={data.cats} selected={selected} now={data.now} onSelect={setSelected} />
        <main class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-panel border-2 border-line bg-paper shadow-sticker">
          <CatHeader cat={cat} now={data.now} onForgotten={() => { setSelected("*"); refresh(); }} />
          {cat && (
            <nav class="grid shrink-0 grid-cols-3 gap-1 border-b-2 border-line bg-paper-2 px-1.5 pt-1.5 sm:flex sm:px-4 sm:pt-3 md:px-5">
              {TABS.map(([k, label, short, icon]) => (
                <button key={k} onClick={() => setTab(k)} aria-current={current === k ? "page" : undefined}
                  class={cx("-mb-0.5 flex min-w-0 items-center justify-center gap-1.5 rounded-t-chip border-2 border-b-0 px-1 py-2 font-pixel text-sm xs:text-base sm:gap-2 sm:px-3.5",
                    current === k ? "border-line bg-paper" : "border-transparent text-ink-soft hover:text-ink")}>
                  <PixelIcon name={icon} class="hidden size-4.5 xs:block" />
                  <span class="truncate sm:hidden">{short}</span>
                  <span class="hidden sm:inline">{label}</span>
                </button>
              ))}
            </nav>
          )}
          {current === "chat" && <ChatPane selected={selected} send={send} feedVersion={feedVersion} />}
          {current === "settings" && <SettingsPane key={cat.id} cat={cat} store={store} send={send} />}
          {current === "phrases" && <PhrasesPane key={cat.id} cat={cat} send={send} />}
        </main>
      </div>
    </section>
  );
}
