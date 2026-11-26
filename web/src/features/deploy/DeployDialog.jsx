import { useEffect, useRef, useState } from "preact/hooks";
import { Note } from "../../components/Note.jsx";
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

  if (error) return <Note icon="⚠️" warn>Erreur : {error}</Note>;
  if (!d) return <div class="muted">Chargement…</div>;
  const reload = () => load(true);

  let body;
  if (!d.has_deploy) {
    body = (
      <Note icon="🔧">
        Le déploiement depuis GitHub n'est pas encore configuré sur le serveur (commande « setup-deploy », voir le README).
      </Note>
    );
  } else if (!d.has_token || changeToken) {
    body = <TokenForm d={d} change={d.has_token} onSaved={() => { setChangeToken(false); reload(); }} />;
  } else {
    body = (
      <>
        <PublishPanel d={d} now={now} reload={reload} />
        <button class="linkbtn" onClick={() => setChangeToken(true)}>Changer le token GitHub</button>
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

export function DeployDialog({ open, onClose, cats, now }) {
  const [dialog, setDialog] = useState(null);
  useEffect(() => {
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open, dialog]);
  return (
    <dialog class="deploy" ref={setDialog} onClose={onClose}>
      <div class="dlg-head">
        <h2>🚀 Mises à jour</h2>
        <button class="ib" title="Fermer" onClick={onClose}>✖️</button>
      </div>
      <div class="dlg-body">{open && <DeployBody cats={cats} now={now} />}</div>
    </dialog>
  );
}
