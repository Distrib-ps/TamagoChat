export class AuthError extends Error {}

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export async function api(path, body) {
  const opts = { credentials: "same-origin" };
  if (body !== undefined) {
    Object.assign(opts, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  }
  const r = await fetch(path, opts);
  if (r.status === 401 && !path.endsWith("/login")) { onUnauthorized(); throw new AuthError("auth"); }
  if (!r.ok) throw new Error(await r.text() || r.statusText);
  return r.json();
}

// pour les rafraîchissements automatiques : les erreurs passagères ne sont pas affichées
export const quiet = (e) => { if (!(e instanceof AuthError)) console.warn(e); };
