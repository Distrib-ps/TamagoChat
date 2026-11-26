export const ACTION_GROUPS = [
  ["Soins", [["feed", "Manger", "food"], ["drink", "Boire", "water"], ["pet", "Caresse", "pet"],
             ["love", "Pluie de câlins", "hearts"], ["play", "Pelote", "yarn"], ["sleep", "Sieste", "sleep"],
             ["wake", "Réveiller", "wake"], ["meow", "Miaou", "paw"]]],
  ["Bêtises", [["crazy", "Crise de folie", "crazy"], ["crazy_xl", "Folie XXL (30 s)", "crazy"],
               ["flies", "Mouches", "flies"], ["swarm", "Nuée de mouches", "flies"], ["jump", "Grand saut", "jump"],
               ["drop", "Tomber du ciel", "comet"], ["screen", "Changer d'écran", "screen"],
               ["mouse", "Chasser la souris", "mouse"], ["hide", "Cache-cache", "box"]]],
  ["Réactions", [["groom", "Toilette", "tongue"], ["stretch", "Étirement", "star"], ["sneeze", "Atchoum", "sneeze"],
                 ["chase_tail", "Courir après sa queue", "spiral"]]],
];
export const ACTION_LABEL = Object.fromEntries(ACTION_GROUPS.flatMap((g) => g[1].map(([k, label]) => [k, label])));
export const ACTION_ICON = Object.fromEntries(ACTION_GROUPS.flatMap((g) => g[1].map(([k, , icon]) => [k, icon])));

export const STATES = {
  idle: "tranquille", walk: "se promène", sleep: "dort", eat: "mange", drink: "boit",
  play: "joue à la pelote", pet: "se fait câliner", crazy: "fait une crise de folie !",
  hunt: "chasse une mouche", drag: "est porté", fall: "tombe", hidden: "joue à cache-cache",
  groom: "fait sa toilette", stretch: "s'étire", sneeze: "éternue", chase_tail: "court après sa queue",
};

export const STATS = [["satiete", "Satiété"], ["hydratation", "Hydratation"], ["bonheur", "Bonheur"], ["energie", "Énergie"]];
export const STAT_LABEL = Object.fromEntries(STATS);
export const STAT_ICON = { satiete: "food", hydratation: "water", bonheur: "pet", energie: "wake" };

export const CHATTER = [[30, "Très souvent (~30 s)"], [60, "Souvent (~1 min)"], [180, "Normal (~3 min)"],
  [600, "Rarement (~10 min)"], [1800, "Très rarement (~30 min)"], [0, "Jamais"]];
export const CRAZY = [[0, "Désactivé"], [30, "Rarement (~30 min)"], [10, "Parfois (~10 min)"], [3, "Souvent (~3 min)"]];
export const FLIES = [[0, "Désactivées"], [20, "Rarement (~20 min)"], [8, "Parfois (~8 min)"], [3, "Souvent (~3 min)"]];
export const SIZES = ["Petit", "Moyen", "Grand"];
export const SET_LABEL = { name: "Nom", autowalk: "Promenade", topmost: "Premier plan", size: "Taille",
  chatter_s: "Phrases spontanées", crazy_min: "Mode FOU", flies_min: "Mouches" };

export const BUBBLE_SECS = [["", "durée auto"], ["15", "15 s"], ["30", "30 s"], ["60", "1 min"], ["120", "2 min"], ["300", "5 min"]];

export const RUN_STATE = { queued: "En file d'attente", in_progress: "Compilation en cours", waiting: "En attente",
  requested: "Demandé", pending: "En attente" };
export const RUN_END = { success: "Publiée", failure: "Échec", cancelled: "Annulée", timed_out: "Trop longue" };

// libellés des catégories de phrases, appris en les chargeant (pour le fil de conversation)
export const phraseLabels = {};
