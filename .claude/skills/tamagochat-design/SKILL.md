---
name: tamagochat-design
description: Identité visuelle « Sticker pixel » de TamagoChat et règles d'interface. À charger avant de créer ou modifier un écran, un composant ou un style de la page admin (web/), ou le style du menu du chat (tamagochat/theme.py).
---

# TamagoChat : identité « Sticker pixel »

## Le sujet

TamagoChat est un chat en pixel art qui vit sur la barre des tâches de quelques amis (Windows et Mac).
La page admin (`web/`) sert à ses propriétaires à voir quels chats sont allumés, à leur envoyer des
messages et des bêtises, à régler leur comportement et à publier les mises à jour. Elle s'utilise
surtout sur ordinateur, parfois sur téléphone. Le ton est joueur, mais la page reste un outil :
on doit trouver une action en un coup d'œil.

L'identité vient du chat lui-même : ses sprites, son contour brun, ses couleurs. La page admin et le
menu du clic droit de l'app (`tamagochat/theme.py`, `tamagochat/icons.py`) partagent le même style.

## Le style

Des autocollants : surfaces pleines entourées d'un contour brun épais, posées sur un ciel bleu pâle,
avec une ombre pleine décalée (jamais floue). Les couleurs vives viennent des sprites et portent du
sens (une jauge, un état, une action), elles ne décorent pas.

| Jeton (`--color-*`) | Clair | Sombre | Rôle |
|---|---|---|---|
| `sky` | `#dcecf5` | `#17202a` | fond de la page |
| `paper` | `#ffffff` | `#2b231e` | surfaces (panneaux, boutons, bulles) |
| `paper-2` | `#f3f8fb` | `#221c18` | fond du fil de conversation, zones creuses |
| `line` | `#3b2a22` | `#0c0907` | contours et ombres pleines |
| `ink` | `#3b2a22` | `#f4e6d8` | texte |
| `ink-soft` | `#7d6a60` | `#b8a597` | texte secondaire |
| `fur` | `#f2a65a` | `#e8944a` | accent : en-tête du chat, bouton principal |
| `fur-soft` | `#ffe1c2` | `#4a3322` | sélection, mes messages |
| `leaf` | `#7bc46a` | | en ligne, réussite |
| `water`, `rose`, `sun` | `#5aa9e6`, `#e8557a`, `#ffd84a` | | jauges et icônes |

Les couleurs des jauges sont fixes : satiété `#e8a23c`, hydratation `#4fa3e0`, bonheur `#e8557a`,
énergie `#7bc46a` (les mêmes que dans l'app).

- **Polices** : Pixelify Sans (`font-pixel`) pour le nom de l'app, les noms des chats, les titres et
  les onglets ; Atkinson Hyperlegible (`font-sans`) pour tout le reste. Elles sont installées par npm
  (`@fontsource/*`), jamais chargées depuis Google : la page n'accepte que ses propres fichiers (CSP).
- **Contours** : 2 px `line` sur tout ce qui est posé (panneaux, boutons, champs, bulles, jauges).
- **Ombres** : pleines et décalées, `shadow-sticker` (4 px) pour les panneaux, `shadow-sticker-sm`
  (2 px) pour les boutons. Un bouton enfoncé perd son ombre et se décale d'autant.
- **Arrondis** : 16 px pour les panneaux, 10 px pour les boutons et champs, carrés pour les pastilles
  d'état et les jauges (rappel des pixels).
- **Icônes** : uniquement les icônes en pixel art de `src/lib/icons.js` (composant `PixelIcon`),
  jamais d'emojis. Une icône manquante se dessine dans la grille 9 x 9 avec la palette des sprites ;
  celles du menu de l'app doivent rester identiques à `tamagochat/icons.py` (vérifié par les tests).
- **Mouvement** : seulement en réponse à ce que fait la personne ou à ce qui arrive, jamais en boucle.
  Les animations sont des jetons de `app.css` : `animate-hop` (le chat saute quand on le sélectionne,
  l'icône d'une action bondit quand elle est envoyée), `animate-pop` (nouveau message, fenêtre qui
  s'ouvre), `animate-fade` (changement d'onglet), `animate-drop` (tiroir qui s'ouvre), `animate-rise`
  (notification). Les jauges glissent vers leur nouvelle valeur. Tout est coupé quand le système
  demande moins d'animations (règle globale dans `app.css`).

## Ce qu'on s'interdit

Ce sont les marques d'une interface générée, que la page avait avant :
- les étiquettes en majuscules ou espacées (« SOINS ») : écrire « Soins » ;
- les infos collées avec des points médians (« 2 en ligne · 4 chats ») : faire une phrase
  (« 2 chats en ligne sur 4 ») ou séparer visuellement ;
- les flèches et emojis dans les textes et boutons (« Jauges → », « 🚀 Publier ») ;
- les cartes identiques à ombre grise floue et les dégradés décoratifs ;
- le fond crème avec un accent orangé seul.

## Écrire les textes

En français, au tutoiement, en phrases simples, majuscule seulement au début. Un bouton dit ce qu'il
fait (« Envoyer », « Renommer », « Publier la version 1.5.0 ») et le message qui suit reprend le même
mot (« Envoyé »). Une erreur dit ce qui s'est passé et quoi faire, sans s'excuser. Un écran vide
propose quoi faire.

## Tailwind

- Tailwind v4 avec `@tailwindcss/vite` : pas de fichier de configuration. Les jetons sont dans le
  bloc `@theme` de `src/styles/app.css`, et le mode sombre redéfinit les mêmes variables.
- Les classes Tailwind vont dans le JSX. Pas de couleur en dur (`#...` ou `bg-[...]`) dans les
  composants : seulement les jetons ci-dessus.
- Ce qui se répète passe par les composants de `src/components/ui.jsx` (`Button`, `Panel`, `Field`,
  `Badge`…) plutôt que de recopier les mêmes classes.
- `app.css` ne contient que l'import de Tailwind, des polices, les jetons et quelques styles de base
  (éléments natifs comme `select` ou `input[type=range]`).

## Qualité minimale

- **Téléphone et tablette (moins de 1024 px)** : la page est une appli qui tient dans l'écran
  (`h-dvh`). Seul le contenu de l'onglet défile, et la saisie reste en bas. Le chat choisi s'affiche
  dans un bouton « Changer » qui ouvre le sélecteur plein écran (`CatPicker`). Les onglets prennent
  des libellés courts, les actions passent dans un tiroir, les menus déroulants sous leur libellé
  (`Field stack`) et les jauges sur une ligne avec leurs icônes. Les fenêtres (`Dialog`) occupent tout
  l'écran sous 640 px.
- **Ordinateur (1024 px et plus)** : la liste des chats est une colonne qui défile seule.
- **Beaucoup de chats** (le serveur en accepte 500) : la recherche et le filtre « En ligne »
  apparaissent dès 6 chats, et les listes défilent dans leur cadre, jamais la page entière.
- **Rien ne déborde, de 320 px à l'ordinateur** : une grille qui doit rétrécir utilise
  `grid-cols-[minmax(0,1fr)]`, et un champ dans une rangée `min-w-0`. Les marges de droite et du bas
  sont plus larges de la taille de l'ombre (`pr-4` pour `pl-3`), pour que les panneaux paraissent
  centrés.
- Focus clavier visible sur tout ce qui se clique (`focus-visible:outline`).
- Contraste suffisant en clair et en sombre (texte `ink-soft` réservé aux infos secondaires).

## Vérifier avant de dire que c'est fini

1. `cd web && npm run dev` : la page s'ouvre avec des chats de démo (mot de passe `admin`).
2. Regarder l'écran modifié dans le navigateur (capture), en clair et en sombre, à 320 px, 400 px,
   768 px (tablette), 1024 px et pleine largeur, avec beaucoup de chats et de longs textes, et
   vérifier qu'il n'y a pas d'erreur dans la console. Une iframe de la taille voulue dans la page
   suffit quand la fenêtre du navigateur ne se redimensionne pas.
3. `npm run build`, puis les tests : `python3 -m unittest discover -s tests` à la racine et
   `cd server && .venv/bin/python -m unittest discover -s tests` (la page compilée est servie par
   le serveur).
