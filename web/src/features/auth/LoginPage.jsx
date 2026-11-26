import { useState } from "preact/hooks";
import { api } from "../../lib/api.js";
import { CAT_IMAGE } from "../../lib/assets.js";

export function LoginPage({ onLogin }) {
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api("/admin/api/login", { password: pw });
      setPw("");
      onLogin();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <section class="login">
      <form class="card" onSubmit={submit}>
        <img class="logo" src={CAT_IMAGE} alt="" />
        <h1>Centre de contrôle TamagoChat</h1>
        <p>Envoie des messages et des bêtises aux chats.</p>
        <input type="password" placeholder="Mot de passe" autocomplete="current-password" required
               value={pw} onInput={(e) => setPw(e.currentTarget.value)} />
        <button class="btn" type="submit">Entrer</button>
        <div class="err">{err}</div>
      </form>
    </section>
  );
}
