import { CAT_IMAGE } from "../lib/assets.js";
import { plural } from "../lib/format.js";

export function Header({ data, onDeploy, onLogout }) {
  const online = data.cats.filter((c) => c.online).length;
  let release = data.release ? `🚀 v${data.release.version}` : "🚀 Mises à jour";
  if (data.release_mac && data.release_mac.version !== data.release?.version) {
    release += ` · Mac v${data.release_mac.version}`;
  }
  return (
    <header>
      <h1><img src={CAT_IMAGE} alt="" /> TamagoChat</h1>
      <span class="badge online">{online} en ligne · {plural(data.cats.length, "chat")}</span>
      <span class="spacer" />
      <button class="badge relbtn" title="Mises à jour" onClick={onDeploy}>{release}</button>
      <button class="linkbtn" onClick={onLogout}>Se déconnecter</button>
    </header>
  );
}
