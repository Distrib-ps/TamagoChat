import { PixelIcon, cx } from "./ui.jsx";

export const Note = ({ icon = "phrases", warn, children }) => (
  <div class={cx("flex items-start gap-2.5 rounded-chip border-2 border-line px-3.5 py-2.5 text-sm", warn ? "bg-warn" : "bg-paper-2")}>
    <PixelIcon name={icon} class="mt-0.5 size-4.5" />
    <span>{children}</span>
  </div>
);
