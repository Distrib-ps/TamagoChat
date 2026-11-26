import { useState } from "preact/hooks";
import { toast } from "../../components/Toasts.jsx";
import { AuthError, api } from "../../lib/api.js";

export function TokenForm({ d, change, onSaved }) {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api("/admin/api/deploy/token", { token: token.trim() });
      toast(r.ok ? "Token enregistré ✓" : "Token enregistré, mais GitHub refuse : " + r.error);
      setToken("");
      onSaved();
    } catch (err) {
      if (!(err instanceof AuthError)) toast("Erreur : " + err.message);
    }
    setBusy(false);
  };
  return (
    <section>
      <h3>{change ? "Changer le token GitHub" : "Connecter GitHub (une seule fois)"}</h3>
      <ol class="steps">
        <li>
          <a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">
            Crée un token GitHub « fine-grained »
          </a>{" "}
          avec le compte propriétaire de {d.repo || "ton dépôt"}.
        </li>
        <li>Repository access : « Only select repositories » → {d.repo ? d.repo.split("/")[1] : "le dépôt"}.</li>
        <li>Permissions : Actions → « Read and write », Contents → « Read-only ».</li>
        <li>Expiration : au choix (1 an par exemple). Copie le token et colle-le ici.</li>
      </ol>
      <form class="tokform" onSubmit={submit}>
        <input type="password" placeholder="github_pat_…" autocomplete="off" value={token}
               onInput={(e) => setToken(e.currentTarget.value)} />
        <button class="btn" disabled={busy}>Enregistrer</button>
      </form>
      <div class="muted">
        Le token reste sur ton serveur (jamais renvoyé à la page). Il ne peut que lancer la compilation de ce dépôt.
      </div>
    </section>
  );
}
