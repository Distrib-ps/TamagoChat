import { Button, IconButton, LinkButton } from "../components/ui.jsx";
import { CAT_IMAGE } from "../lib/assets.js";

export function Header({ data, onDeploy, onLogout }) {
  const online = data.cats.filter((c) => c.online).length;
  let release = data.release ? `Version ${data.release.version}` : "Mises à jour";
  if (data.release_mac && data.release_mac.version !== data.release?.version) {
    release += `, Mac ${data.release_mac.version}`;
  }
  return (
    <header class="flex shrink-0 items-center gap-x-4 py-2.5 pr-4 pl-3 sm:pr-5 sm:pl-4 lg:py-4 lg:pr-7 lg:pl-6">
      <h1 class="flex items-center gap-2 font-pixel text-xl font-bold md:gap-2.5 md:text-2xl">
        <img src={CAT_IMAGE} alt="" class="w-8 [image-rendering:pixelated] md:w-9" />
        TamagoChat
      </h1>
      <span class="hidden text-sm text-ink-soft sm:inline">
        {online} {online > 1 ? "chats en ligne" : "chat en ligne"} sur {data.cats.length}
      </span>
      <span class="ml-auto flex items-center gap-3 md:gap-4">
        <Button size="sm" icon="jump" title="Mises à jour" aria-label="Mises à jour" onClick={onDeploy}>
          <span class="hidden sm:inline">{release}</span>
        </Button>
        <LinkButton class="hidden sm:inline" onClick={onLogout}>Se déconnecter</LinkButton>
        <IconButton icon="quit" label="Se déconnecter" class="sm:hidden" onClick={onLogout} />
      </span>
    </header>
  );
}
