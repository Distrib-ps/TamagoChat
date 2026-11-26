// Fichiers de public/ : à la racine en développement, sous /admin/static/ une fois compilé.
export const asset = (path) => import.meta.env.BASE_URL + path;
export const CAT_IMAGE = asset("images/cat.png");
