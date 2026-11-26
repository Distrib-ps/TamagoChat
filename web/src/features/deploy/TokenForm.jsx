import { useState } from "preact/hooks";
import { toast } from "../../components/Toasts.jsx";
import { Button, PanelTitle, control, cx } from "../../components/ui.jsx";
import { AuthError, api } from "../../lib/api.js";

export function TokenForm({ d, change, onSaved }) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api("/admin/api/deploy/token", { token: token.trim() });
      toast(r.ok ? "Token enregistré" : "Token enregistré, mais GitHub le refuse : " + r.error);
      setToken("");
      onSaved();
    } catch (err) {
      if (!(err instanceof AuthError)) toast("Erreur : " + err.message);
    }
    setBusy(false);
  };
  return (
    <section class="grid gap-3">
      <PanelTitle>{change ? "Changer le token GitHub" : "Connecter GitHub (une seule fois)"}</PanelTitle>
      <ol class="grid list-decimal gap-1.5 pl-5">
        <li>
          <a class="font-bold underline underline-offset-2" href="https://github.com/settings/personal-access-tokens/new"
             target="_blank" rel="noopener">Crée un token GitHub « fine-grained »</a>{" "}
          avec le compte propriétaire de {d.repo || "ton dépôt"}.
        </li>
        <li>Repository access : « Only select repositories », puis {d.repo ? d.repo.split("/")[1] : "le dépôt"}.</li>
        <li>Permissions : Actions en « Read and write », Contents en « Read-only ».</li>
        <li>Expiration : au choix (1 an par exemple). Copie le token et colle-le ici.</li>
      </ol>
      <form onSubmit={submit} class="flex flex-wrap gap-2">
        <input type="password" placeholder="github_pat_…" autocomplete="off" aria-label="Token GitHub" value={token}
               class={cx(control, "min-w-48 flex-1")} onInput={(e) => setToken(e.currentTarget.value)} />
        <Button variant="primary" type="submit" disabled={busy}>Enregistrer</Button>
      </form>
      <p class="text-sm text-ink-soft">
        Le token reste sur ton serveur et n'est jamais renvoyé à la page. Il ne peut que lancer la compilation de ce dépôt.
      </p>
    </section>
  );
}
