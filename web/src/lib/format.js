import { ACTION_LABEL, SET_LABEL, STAT_LABEL, phraseLabels } from "../constants.js";

export function ago(ts, now) {
  if (!ts) return "jamais";
  const s = Math.max(0, now - ts);
  if (s < 60) return "à l'instant";
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  return `il y a ${Math.floor(s / 86400)} j`;
}
export const isoAgo = (iso, now) => ago(Date.parse(iso) / 1000, now);

export const hhmm = (ts) => new Date(ts * 1000).toLocaleString("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit" });

export function fmtDelay(s) {
  if (!s) return "jamais";
  return s < 60 ? `${s} s` : `${+(s / 60).toFixed(1)} min`.replace(".", ",");
}

export function describeSetting(k, v) {
  if (k === "autowalk" || k === "topmost") return `${SET_LABEL[k]} : ${v ? "oui" : "non"}`;
  if (k === "chatter_s") return `${SET_LABEL[k]} : ${v ? "~" + fmtDelay(v) : "jamais"}`;
  if (k === "crazy_min" || k === "flies_min") return `${SET_LABEL[k]} : ${v ? "~" + v + " min" : "désactivé"}`;
  return `${SET_LABEL[k] || k} : ${v}`;
}

export function describeItem(it) {
  if (it.kind === "action") return ACTION_LABEL[it.action] || it.action;
  if (it.kind === "settings") return "⚙️ " + Object.entries(it.settings || {}).map(([k, v]) => describeSetting(k, v)).join(" · ");
  if (it.kind === "stats") return "📊 Jauges → " + Object.entries(it.stats || {}).map(([k, v]) => `${STAT_LABEL[k] || k} ${v}`).join(" · ");
  if (it.kind === "phrases") {
    const label = phraseLabels[it.key] || it.key;
    return `🗨️ Phrases « ${label} » : ` + (it.reset ? "remises d'origine" : `${(it.list || []).length} phrase(s)`);
  }
  return it.kind;
}

// même règle que semantic-release (Conventional Commits) : feat! -> majeure, feat -> mineure, fix -> correctif
export function bumpOf(commits) {
  let level = 0;
  for (const c of commits) {
    const m = /^(\w+)(\([^)]*\))?(!)?:/.exec(c.message);
    if (!m) continue;
    if (m[3] || /BREAKING CHANGE/.test(c.message)) return 3;
    if (m[1] === "feat") level = Math.max(level, 2);
    else if (m[1] === "fix" || m[1] === "perf") level = Math.max(level, 1);
  }
  return level;
}

export function nextVersion(v, level) {
  if (!v || !level) return "";
  const p = v.split(".").map(Number);
  if (level === 3) return `${p[0] + 1}.0.0`;
  if (level === 2) return `${p[0]}.${p[1] + 1}.0`;
  return `${p[0]}.${p[1]}.${p[2] + 1}`;
}

export const plural = (n, word) => `${n} ${word}${n > 1 ? "s" : ""}`;
