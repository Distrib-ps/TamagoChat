import { ICONS, PALETTE } from "../lib/icons.js";

export const cx = (...classes) => classes.filter(Boolean).join(" ");

const runsCache = {};
// Icônes au corps blanc (enveloppe, bulle) : leur contour reste brun, comme un autocollant, sinon
// en sombre le contour crème se confond avec le blanc et l'icône devient un rectangle.
const PAPER_ICONS = new Set(["message", "phrases"]);
// Le contour (K) des autres icônes suit la couleur du texte : brun en clair, crème en sombre.
function iconRuns(name) {
  const outline = PAPER_ICONS.has(name) ? "var(--color-line)" : "currentColor";
  return (runsCache[name] ||= ICONS[name].flatMap((row, y) => {
    const runs = [];
    for (let x = 0; x < row.length;) {
      let end = x;
      while (end < row.length && row[end] === row[x]) end++;
      if (row[x] !== ".") runs.push([x, y, end - x, row[x] === "K" ? outline : PALETTE[row[x]]]);
      x = end;
    }
    return runs;
  }));
}

export const PixelIcon = ({ name, class: cls }) => (
  <svg viewBox="0 0 9 9" class={cx("shrink-0", cls || "size-4.5")} shape-rendering="crispEdges" aria-hidden="true">
    {iconRuns(name).map(([x, y, w, fill]) => <rect key={`${x}-${y}`} x={x} y={y} width={w} height={1} fill={fill} />)}
  </svg>
);

const BUTTON = {
  primary: "bg-fur font-bold text-line hover:brightness-105",
  plain: "bg-paper text-ink hover:bg-fur-soft",
};
const SIZE = { md: "px-3 py-2 xs:px-4", sm: "px-2.5 py-1 text-sm" };

export const Button = ({ variant = "plain", size = "md", icon, class: cls, children, ...props }) => (
  <button
    type="button"
    {...props}
    class={cx(
      "inline-flex items-center justify-center gap-2 rounded-chip border-2 border-line shadow-sticker-sm",
      "transition-[translate,box-shadow] duration-75 motion-reduce:transition-none",
      "active:translate-0.5 active:shadow-none disabled:opacity-50 disabled:shadow-none disabled:active:translate-0",
      BUTTON[variant], SIZE[size], cls,
    )}
  >
    {icon && <PixelIcon name={icon} />}
    {children}
  </button>
);

export const LinkButton = ({ class: cls, children, ...props }) => (
  <button type="button" {...props}
    class={cx("rounded-sm text-sm text-ink-soft underline-offset-2 hover:text-ink hover:underline disabled:opacity-50", cls)}>
    {children}
  </button>
);

export const IconButton = ({ icon, label, class: cls, ...props }) => (
  <button type="button" title={label} aria-label={label} {...props}
    class={cx("inline-flex size-8 shrink-0 items-center justify-center rounded-chip hover:bg-fur-soft disabled:opacity-40", cls)}>
    <PixelIcon name={icon} />
  </button>
);

export const Panel = ({ as: Tag = "div", class: cls, children, ...props }) => (
  <Tag {...props} class={cx("rounded-panel border-2 border-line bg-paper shadow-sticker", cls)}>{children}</Tag>
);

export const PanelTitle = ({ icon, children }) => (
  <h3 class="flex items-center gap-2 font-pixel text-lg">
    {icon && <PixelIcon name={icon} class="size-5" />}
    {children}
  </h3>
);

export const control = cx(
  "rounded-chip border-2 border-line bg-paper px-3 py-2 text-ink placeholder:text-ink-soft",
  "disabled:opacity-60 focus-visible:outline-offset-0",
);

export const Segmented = ({ value, options, onChange, disabled, class: cls }) => (
  <div class={cx("inline-flex overflow-hidden rounded-chip border-2 border-line", cls)}>
    {options.map(([v, label]) => (
      <button type="button" key={v} disabled={disabled} aria-pressed={v === value} onClick={() => onChange(v)}
              class={cx("flex-1 border-l-2 border-line px-3 py-1.5 text-sm whitespace-nowrap first:border-l-0 disabled:opacity-50",
                v === value ? "bg-fur font-bold text-line" : "bg-paper hover:bg-fur-soft")}>{label}</button>
    ))}
  </div>
);

export const Badge = ({ class: cls, children }) => (
  <span class={cx("inline-flex items-center rounded-full border-2 border-line px-2 text-xs font-bold", cls)}>{children}</span>
);

export const StatusDot = ({ on, class: cls }) => (
  <span class={cx("inline-block size-2.5 shrink-0 border-2 border-line", on ? "bg-leaf" : "bg-paper-2", cls)} />
);

export function GaugeBar({ stat, value, thin, class: cls }) {
  return (
    <span class={cx("block border-line bg-paper-2", thin ? "border" : "border-2", cls)}>
      <span class="block h-full transition-[width] duration-500 ease-out" style={{ width: `${value}%`, background: `var(--color-${stat})` }} />
    </span>
  );
}
