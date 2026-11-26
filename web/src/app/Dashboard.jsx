import { useEffect, useRef, useState } from "preact/hooks";
import { toast } from "../components/Toasts.jsx";
import { CatHeader } from "../features/cats/CatHeader.jsx";
import { CatList } from "../features/cats/CatList.jsx";
import { ChatPane } from "../features/chat/ChatPane.jsx";
import { DeployDialog } from "../features/deploy/DeployDialog.jsx";
import { PhrasesPane } from "../features/phrases/PhrasesPane.jsx";
import { SettingsPane } from "../features/settings/SettingsPane.jsx";
import { AuthError, api } from "../lib/api.js";
import { Header } from "./Header.jsx";

const TABS = [["chat", "💬 Messages & actions"], ["settings", "⚙️ Réglages & jauges"], ["phrases", "🗨️ Phrases"]];

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
    <section class="app">
      <Header data={data} onDeploy={() => setDeployOpen(true)} onLogout={onLogout} />
      <DeployDialog open={deployOpen} onClose={() => setDeployOpen(false)} cats={data.cats} now={data.now} />
      <div class="layout">
        <CatList cats={data.cats} selected={selected} now={data.now} onSelect={setSelected} />
        <main>
          <CatHeader cat={cat} now={data.now} onForgotten={() => { setSelected("*"); refresh(); }} />
          {cat && (
            <nav class="tabs">
              {TABS.map(([k, label]) => (
                <button class={"tab" + (current === k ? " sel" : "")} key={k} onClick={() => setTab(k)}>{label}</button>
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
