export const ACTION_GROUPS = [
  ["Soins", [["feed", "🍗 Manger"], ["drink", "💧 Boire"], ["pet", "💗 Caresse"], ["love", "💞 Pluie de câlins"],
             ["play", "🧶 Pelote"], ["sleep", "😴 Sieste"], ["wake", "⏰ Réveiller"], ["meow", "🐾 Miaou"]]],
  ["Bêtises", [["crazy", "🌀 Crise de folie"], ["crazy_xl", "🌪️ Folie XXL (30 s)"], ["flies", "🪰 Mouches"],
               ["swarm", "🪰🪰 Nuée de mouches"], ["jump", "🦘 Grand saut"], ["drop", "☄️ Tomber du ciel"],
               ["screen", "🖥️ Changer d'écran"], ["mouse", "🖱️ Chasser la souris"], ["hide", "🙈 Cache-cache"]]],
  ["Réactions", [["groom", "👅 Toilette"], ["stretch", "🥱 Étirement"], ["sneeze", "🤧 Atchoum"],
                 ["chase_tail", "🐈 Courir après sa queue"]]],
];
export const ACTION_LABEL = Object.fromEntries(ACTION_GROUPS.flatMap(g => g[1]));

export const STATES = {
  idle: "tranquille", walk: "se promène", sleep: "dort", eat: "mange", drink: "boit",
  play: "joue à la pelote", pet: "se fait câliner", crazy: "fait une crise de folie !",
  hunt: "chasse une mouche", drag: "est porté", fall: "tombe", hidden: "joue à cache-cache 🙈",
  groom: "fait sa toilette", stretch: "s'étire", sneeze: "éternue", chase_tail: "court après sa queue",
};

export const STATS = [["satiete", "Satiété"], ["hydratation", "Hydratation"], ["bonheur", "Bonheur"], ["energie", "Énergie"]];
export const STAT_LABEL = Object.fromEntries(STATS);

export const CHATTER = [[30, "Très souvent (~30 s)"], [60, "Souvent (~1 min)"], [180, "Normal (~3 min)"],
  [600, "Rarement (~10 min)"], [1800, "Très rarement (~30 min)"], [0, "Jamais"]];
export const CRAZY = [[0, "Désactivé"], [30, "Rarement (~30 min)"], [10, "Parfois (~10 min)"], [3, "Souvent (~3 min)"]];
export const FLIES = [[0, "Désactivées"], [20, "Rarement (~20 min)"], [8, "Parfois (~8 min)"], [3, "Souvent (~3 min)"]];
export const SIZES = ["Petit", "Moyen", "Grand"];
export const SET_LABEL = { name: "Nom", autowalk: "Promenade", topmost: "Premier plan", size: "Taille",
  chatter_s: "Phrases spontanées", crazy_min: "Mode FOU", flies_min: "Mouches" };

export const BUBBLE_SECS = [["", "durée auto"], ["15", "15 s"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"]];

export const RUN_STATE = { queued: "⏳ en file d'attente", in_progress: "🔨 compilation en cours…", waiting: "⏳ en attente",
  requested: "⏳ demandé", pending: "⏳ en attente" };
export const RUN_END = { success: "✅ publiée", failure: "❌ échec", cancelled: "⛔ annulée", timed_out: "❌ trop longue" };

// libellés des catégories de phrases, appris en les chargeant (pour le fil de conversation)
export const phraseLabels = {};
