import { useState } from "preact/hooks";
import { Note } from "../../components/Note.jsx";
import { toast } from "../../components/Toasts.jsx";
import { Button, PanelTitle, cx } from "../../components/ui.jsx";
import { RUN_END, RUN_STATE } from "../../constants.js";
import { AuthError, api } from "../../lib/api.js";
import { bumpOf, isoAgo, nextVersion, plural } from "../../lib/format.js";

const ExtLink = ({ href, children }) => (
  <a class="min-w-[min(100%,14rem)] flex-1 [overflow-wrap:anywhere] hover:underline" href={href} target="_blank" rel="noopener">{children}</a>
);
const List = ({ children }) => (
  <ul class="divide-y-2 divide-line/15 overflow-hidden rounded-chip border-2 border-line">{children}</ul>
);
const Row = ({ children }) => (
  <li class="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 px-3 py-2 text-sm">{children}</li>
);
const RUN_COLOR = { success: "bg-leaf", failure: "bg-rose", timed_out: "bg-rose", cancelled: "bg-paper-2" };

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
      toast("Compilation lancée sur GitHub (environ 5 min)");
      setTimeout(() => { setLaunching(false); reload(); }, 2500);
    } catch (err) {
      if (!(err instanceof AuthError)) toast("Erreur : " + err.message);
      setLaunching(false);
    }
  };

  const title = !d.base_known ? "Derniers changements sur GitHub"
    : n ? `${plural(n, "changement")} pas encore ${n > 1 ? "déployés" : "déployé"}` : "Changements";
  const label = launching ? "Lancement…" : running ? "Déploiement en cours…"
    : next ? `Publier la version ${next}` : "Compiler et déployer";
  return (
    <>
      {d.error && <Note icon="quit" warn>{d.error}</Note>}
      <section class="grid gap-2">
        <PanelTitle>{title}</PanelTitle>
        {!d.base_known && (
          <p class="text-sm text-ink-soft">La version publiée ne vient pas de GitHub : impossible de savoir lesquels elle contient déjà.</p>
        )}
        {d.base_known && !n && (
          <p class="text-sm text-ink-soft">Rien de nouveau sur GitHub : la version publiée est à jour avec le code.</p>
        )}
        {n > 0 && (
          <List>
            {commits.map((c) => (
              <Row key={c.sha}>
                <ExtLink href={c.url}>{c.message}</ExtLink>
                <span class="text-xs text-ink-soft">{c.sha}, {isoAgo(c.date, now)}</span>
              </Row>
            ))}
          </List>
        )}
      </section>
      <section class="grid gap-2">
        <PanelTitle>Déployer</PanelTitle>
        <form onSubmit={launch}>
          <Button variant="primary" type="submit" icon="jump" disabled={launching || running || nothing}>{label}</Button>
        </form>
        <p class="text-sm text-ink-soft">
          {nothing
            ? "Rien à publier : aucun commit « fix: » ou « feat: » depuis la dernière version (les « chore: », « docs: »… ne changent pas la version)."
            : "Le numéro de version vient des messages de commit : « fix: » donne un correctif, « feat: » une nouveauté. GitHub compile l'app Windows et Mac (environ 5 min), les signe, crée la release et les envoie au serveur. Les chats se mettent à jour dans la minute qui suit."}
        </p>
      </section>
      {d.runs.length > 0 && (
        <section class="grid gap-2">
          <PanelTitle>Historique</PanelTitle>
          <List>
            {d.runs.map((r) => {
              const done = r.status === "completed";
              const st = done ? (RUN_END[r.conclusion] || r.conclusion) : (RUN_STATE[r.status] || r.status);
              return (
                <Row key={r.id}>
                  <span class={cx("size-2.5 shrink-0 self-center border-2 border-line", done ? RUN_COLOR[r.conclusion] || "bg-paper-2" : "bg-sun")} />
                  <ExtLink href={r.url}><b>{st}</b> {r.title || "#" + r.number}</ExtLink>
                  <span class="text-xs text-ink-soft">{isoAgo(r.created, now)}</span>
                </Row>
              );
            })}
          </List>
        </section>
      )}
    </>
  );
}
