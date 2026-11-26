import { useState } from "preact/hooks";
import { Button, Panel, control } from "../../components/ui.jsx";
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
    <section class="flex min-h-full items-center justify-center p-4">
      <Panel as="form" onSubmit={submit} class="flex w-full max-w-sm flex-col gap-4 p-7">
        <img src={CAT_IMAGE} alt="" class="w-20 animate-hop self-center [image-rendering:pixelated]" />
        <div class="text-center">
          <h1 class="font-pixel text-2xl font-bold">TamagoChat</h1>
          <p class="mt-1 text-ink-soft">Envoie des messages et des bêtises aux chats.</p>
        </div>
        <input type="password" placeholder="Mot de passe" autocomplete="current-password" required aria-label="Mot de passe"
               class={control} value={pw} onInput={(e) => setPw(e.currentTarget.value)} />
        <Button variant="primary" type="submit">Entrer</Button>
        {err && <p class="text-sm font-bold text-danger" role="alert">{err}</p>}
      </Panel>
    </section>
  );
}
