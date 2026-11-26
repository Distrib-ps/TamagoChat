import { useRef, useState } from "preact/hooks";
import { Dialog } from "../../components/Dialog.jsx";
import { Note } from "../../components/Note.jsx";
import { LinkButton } from "../../components/ui.jsx";
import { AuthError, api } from "../../lib/api.js";
import { usePolling } from "../../lib/hooks.js";
import { PublishPanel } from "./PublishPanel.jsx";
import { ReleaseSummary } from "./ReleaseSummary.jsx";
import { TokenForm } from "./TokenForm.jsx";

function DeployBody({ cats, now }) {
  const [d, setD] = useState(null);
  const [error, setError] = useState(null);
  const [changeToken, setChangeToken] = useState(false);
  const load = (force) => api("/admin/api/deploy" + (force ? "?force=1" : ""))
    .then((r) => { setD(r); setError(null); })
    .catch((e) => { if (!(e instanceof AuthError)) setError(e.message); });
  const first = useRef(true);           // la première fois, sans le cache du serveur
  usePolling(() => { load(first.current); first.current = false; }, 5000);

  if (error) return <Note icon="quit" warn>Erreur : {error}</Note>;
  if (!d) return <p class="text-ink-soft">Chargement…</p>;
  const reload = () => load(true);

  let body;
  if (!d.has_deploy) {
    body = (
      <Note icon="options">
        Le déploiement depuis GitHub n'est pas encore configuré sur le serveur (commande « setup-deploy », voir le README).
      </Note>
    );
  } else if (!d.has_token || changeToken) {
    body = <TokenForm d={d} change={d.has_token} onSaved={() => { setChangeToken(false); reload(); }} />;
  } else {
    body = (
      <>
        <PublishPanel d={d} now={now} reload={reload} />
        <LinkButton class="justify-self-start" onClick={() => setChangeToken(true)}>Changer le token GitHub</LinkButton>
      </>
    );
  }
  return (
    <>
      <ReleaseSummary d={d} cats={cats} />
      {body}
    </>
  );
}

export const DeployDialog = ({ open, onClose, cats, now }) => (
  <Dialog open={open} onClose={onClose} title="Mises à jour" icon="jump">
    <div class="grid min-h-0 flex-1 content-start gap-5 overflow-y-auto p-4 sm:p-5">
      <DeployBody cats={cats} now={now} />
    </div>
  </Dialog>
);
