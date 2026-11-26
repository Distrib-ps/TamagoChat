import { useState } from "preact/hooks";
import { Note } from "../../components/Note.jsx";
import { toast } from "../../components/Toasts.jsx";
import { RUN_END, RUN_STATE } from "../../constants.js";
import { AuthError, api } from "../../lib/api.js";
import { bumpOf, isoAgo, nextVersion, plural } from "../../lib/format.js";

const ExtLink = ({ href, children }) => (
  <a class="grow" href={href} target="_blank" rel="noopener">{children}</a>
);

export function PublishPanel({ d, now, reload }) {
  const [launching, setLaunching] = useState(false);
  const commits = d.commits.filter((c) => !c.message.startsWith("chore(release)"));
  const n = commits.length;
  const running = d.runs.some((r) => r.status !== "completed");
  const next = d.base_known ? nextVersion(d.release?.version, bumpOf(commits)) : "";
  const nothing = d.base_known && !next;

  const launch = async (e) => {
    e.preventDefault();
    if (!confirm(`Compiler le code de GitHub (Windows et Mac) et l'envoyer à tous les chats${next ? " en version " + next : ""} ?`)) return;
    setLaunching(true);
    try {
      await api("/admin/api/deploy", {});
      toast("C'est parti ! Compilation sur GitHub (~5 min)…");
      setTimeout(() => { setLaunching(false); reload(); }, 2500);
    } catch (err) {
      if (!(err instanceof AuthError)) toast("Erreur : " + err.message);
      setLaunching(false);
    }
  };

  const title = !d.base_known ? "Derniers changements sur GitHub"
    : n ? `${plural(n, "changement")} pas encore ${n > 1 ? "déployés" : "déployé"}` : "Changements";
  const label = launching ? "Lancement…" : running ? "Déploiement en cours…"
    : next ? `🚀 Publier la v${next}` : "🚀 Compiler et déployer";
  return (
    <>
      {d.error && <Note icon="⚠️" warn>{d.error}</Note>}
      <section>
        <h3>{title}</h3>
        {!d.base_known && (
          <div class="muted">La version publiée ne vient pas de GitHub : impossible de savoir lesquels elle contient déjà.</div>
        )}
        {d.base_known && !n && (
          <div class="muted">Rien de nouveau sur GitHub : la version publiée est à jour avec le code.</div>
        )}
        {n > 0 && (
          <ul class="list">
            {commits.map((c) => (
              <li key={c.sha}>
                <ExtLink href={c.url}>{c.message}</ExtLink>
                <span class="muted">{c.sha} · {isoAgo(c.date, now)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section>
        <h3>Déployer</h3>
        <form class="deploy-form" onSubmit={launch}>
          <button class="btn" disabled={launching || running || nothing}>{label}</button>
        </form>
        <div class="muted">
          {nothing
            ? "Rien à publier : aucun commit « fix: » ou « feat: » depuis la dernière version (les « chore: », « docs: »… ne changent pas la version)."
            : "Le numéro de version est calculé d'après les messages de commit (fix: → correctif, feat: → nouveauté). GitHub compile l'app Windows et Mac (~5 min), les signe, crée la release et les envoie au serveur ; les chats se mettent à jour dans la minute qui suit."}
        </div>
      </section>
      {d.runs.length > 0 && (
        <section>
          <h3>Historique</h3>
          <ul class="list">
            {d.runs.map((r) => {
              const st = r.status === "completed" ? (RUN_END[r.conclusion] || r.conclusion) : (RUN_STATE[r.status] || r.status);
              return (
                <li key={r.id}>
                  <ExtLink href={r.url}>{st} · {r.title || "#" + r.number}</ExtLink>
                  <span class="muted">{isoAgo(r.created, now)}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </>
  );
}
