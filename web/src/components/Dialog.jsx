import { useEffect, useState } from "preact/hooks";
import { IconButton, PixelIcon, cx } from "./ui.jsx";

// Plein écran sur téléphone, fenêtre centrée à partir de 640 px.
// tall : hauteur fixe (pour une liste qui défile à l'intérieur), sinon la hauteur du contenu.
export function Dialog({ open, onClose, title, icon, tall, children }) {
  const [el, setEl] = useState(null);
  useEffect(() => {
    if (!el) return;
    if (open && !el.open) el.showModal();
    if (!open && el.open) el.close();
  }, [open, el]);
  return (
    <dialog ref={setEl} onClose={onClose} aria-label={title}
      class={cx(
        "m-0 h-dvh max-h-none w-full max-w-none flex-col overflow-hidden border-line bg-paper text-ink backdrop:bg-line/50 open:flex",
        "sm:m-auto sm:max-h-[calc(100dvh-2rem)] sm:w-[min(40rem,calc(100vw-2rem))] sm:rounded-panel sm:border-2 sm:shadow-sticker",
        tall ? "sm:h-[min(44rem,calc(100dvh-2rem))]" : "sm:h-auto",
      )}>
      <div class="flex shrink-0 items-center justify-between gap-3 border-b-2 border-line bg-fur py-2.5 pr-2 pl-4 text-line sm:pl-5">
        <h2 class="flex items-center gap-2 font-pixel text-xl font-bold">
          {icon && <PixelIcon name={icon} class="size-5" />}{title}
        </h2>
        <IconButton icon="quit" label="Fermer" onClick={onClose} />
      </div>
      {open && children}
    </dialog>
  );
}
