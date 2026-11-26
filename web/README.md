# Page admin TamagoChat (front)

Application [Preact](https://preactjs.com) compilée avec [Vite](https://vite.dev), qui ne fait
qu'appeler l'API du serveur (`server/`). Une fois compilée (`web/dist`), elle est servie par le
serveur à la même adresse que l'API : `/admin`, fichiers sous `/admin/static/`.

## Développer

Prérequis : [Node.js](https://nodejs.org) 22+ et Python 3.

```bash
cd web
npm install        # la première fois
npm run dev
```

`npm run dev` lance l'API (`server/server.py dev` : chats de démo, mot de passe `admin`) et la page
sur http://localhost:5173, qui s'ouvre dans le navigateur. Une modification du code s'affiche
aussitôt, sans recharger. `Ctrl + C` arrête les deux.

```bash
npm run build      # compile dans web/dist (servi par server.py, déployé sur le VPS)
```

Pour juste utiliser la page sans toucher au front, `python3 server/server.py dev` suffit (après un
`npm run build`).

Les ports par défaut (API 8090, page 5173) se changent dans un fichier `web/.env` : copier
`.env.example` (ignoré par git). Le front ne contient aucun secret : tout passe par l'API.

## Organisation

```
web/
├── package.json · vite.config.js · index.html
├── .env.example              ports de `npm run dev` (API_PORT, WEB_PORT)
├── public/                   copié tel quel : favicon.ico (icône du chat), images/cat.png
└── src/
    ├── main.jsx              point d'entrée
    ├── app/                  App (connexion), Dashboard (écran principal), Header
    ├── features/             une partie de l'interface par dossier
    │   ├── auth/             écran de connexion
    │   ├── cats/             liste des chats, en-tête du chat sélectionné
    │   ├── chat/             actions, conversation, saisie d'un message
    │   ├── settings/         nom, jauges, comportement
    │   ├── phrases/          phrases du chat
    │   └── deploy/           fenêtre « Mises à jour »
    ├── components/           composants partagés : Note, Toasts
    ├── lib/                  api (appels au serveur), format, hooks, assets (chemins de public/)
    ├── constants.js          libellés des actions, états, jauges, réglages
    └── styles/               app.css importe theme, base, login, layout, chat, settings, phrases, deploy
```

## API utilisée

Toutes les requêtes passent par `src/lib/api.js` (cookie de session, retour à la connexion en
cas de 401). En développement, Vite les transmet à l'API (`/admin/api` → `127.0.0.1:8090`).
Elles sont décrites côté serveur dans `server/tamagochat_server/api/`.

| Requête | Rôle |
|---|---|
| `POST /admin/api/login` · `logout` | connexion (cookie httponly) |
| `GET /admin/api/state` | chats, versions publiées (toutes les 3 s) |
| `GET /admin/api/feed?cat=` | conversation avec un chat, ou tous (`*`) |
| `GET /admin/api/phrases?cat=` | phrases d'un chat |
| `POST /admin/api/send` | message, action, réglages, jauges ou phrases |
| `POST /admin/api/forget` | retirer un chat de la liste |
| `GET`/`POST /admin/api/deploy` · `deploy/token` | fenêtre « Mises à jour » |
