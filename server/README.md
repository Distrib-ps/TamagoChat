# Serveur TamagoChat

API [aiohttp](https://docs.aiohttp.org) + SQLite, utilisée par :
- les chats de bureau (messages, réglages, mises à jour) ;
- la page admin, le front situé dans [`web/`](../web/README.md) ;
- GitHub Actions, qui y envoie les versions publiées.

Le serveur sert aussi la page admin compilée, à la même adresse que l'API. L'installation sur un
VPS est décrite dans le [README principal](../README.md#serveur-optionnel).

## Organisation

```
server/
├── server.py                 point d'entrée (lancé par systemd) : python server.py --help
├── requirements.txt          aiohttp
├── .env.example              adresse et port d'écoute (voir « Configuration »)
├── tamagochat_server/
│   ├── cli.py                commandes : dev, check, set-password, setup-deploy
│   ├── app.py                assemblage : services partagés, application, middlewares
│   ├── settings.py           constantes, emplacement des données, lecture de .env
│   ├── errors.py             erreurs métier, traduites en codes HTTP
│   ├── validation.py         contrôle de tout ce qui arrive des chats et de la page admin
│   ├── api/                  couche HTTP (routes)
│   │   ├── pages.py          /  et  /admin
│   │   ├── cats.py           /api/sync, /api/reply, /api/latest, /download/…  (chats)
│   │   ├── auth.py           /admin/api/login, logout
│   │   ├── admin.py          /admin/api/state, feed, phrases, send, forget
│   │   └── deploy.py         /admin/api/deploy… (Mises à jour), /api/release (GitHub Actions)
│   ├── services/             logique, sans HTTP
│   │   ├── auth.py           mot de passe, sessions, limite des essais, jeton de publication
│   │   ├── cats.py           chats : identification, état, phrases
│   │   ├── messages.py       file des messages, long polling, réponses
│   │   ├── releases.py       versions publiées : réception, vérification, stockage
│   │   ├── deploy.py         état et lancement de la publication
│   │   ├── github.py         client de l'API GitHub
│   │   └── signing.py        signatures Ed25519
│   ├── storage/
│   │   ├── database.py       schéma SQLite et migrations
│   │   └── config_store.py   config.json
│   └── demo.py               chats de démo du test local
├── tests/                    tests de l'API (contrat avec les chats installés et GitHub Actions)
└── deploy/                   fichiers installés sur le VPS (noms inchangés) : systemd, nginx
```

Une requête traverse `api/` (lecture de la requête, réponse JSON), puis `services/` (logique),
puis `storage/`. Les services lèvent des erreurs de `errors.py`, que `app.py` transforme en réponse
HTTP (code + message).

## Fonctionnement

- **Chats** : chaque chat s'identifie par un identifiant et un secret qu'il a tirés au hasard. Un
  chat inconnu est enregistré à sa première synchronisation. `/api/sync` est un « long polling » :
  la requête attend jusqu'à 25 s qu'un message arrive, et un envoi depuis la page admin la réveille
  aussitôt. Les messages non reçus au bout de 7 jours ne sont plus envoyés.
- **Page admin** : mot de passe hashé (scrypt) dans `config.json`, session par cookie httponly
  (30 jours), 10 essais par adresse IP et par quart d'heure.
- **Versions** : GitHub Actions envoie chaque version à `/api/release` avec le jeton `DEPLOY_TOKEN`.
  Le serveur vérifie le sha256 et la signature Ed25519 avant de la publier, et chaque chat
  la revérifie avant de s'installer. Une plateforme par fichier (`latest.json` pour Windows,
  `latest-mac.json` pour Mac) ; les chats Windows les plus anciens n'annoncent pas de plateforme
  et reçoivent la version Windows. Les 5 dernières versions sont gardées.
- **Données** : `minou.db`, `config.json` et `releases/` sont à côté de `server.py`
  (`/opt/minou-server` sur le VPS, `server/.dev` en test local). `config.json` est relu à chaque
  usage : `set-password` et `setup-deploy` s'appliquent sans redémarrer.
- **Signatures** : sur le VPS, `ed25519.py` (copie de `tamagochat/ed25519.py`) est à côté de
  `server.py` ; dans le dépôt, le serveur prend directement celui de `tamagochat/`.

## Configuration

Aucun secret n'est dans le code ni dans un fichier `.env` :
- le mot de passe admin, le jeton de publication et le token GitHub sont dans `config.json`
  (créé sur le serveur, hashés sauf le token, jamais commité) ;
- la clé de signature et le jeton de publication côté GitHub sont dans les secrets du dépôt.

Seules l'adresse et le port d'écoute sont réglables, avec les variables d'environnement
`TAMAGOCHAT_HOST` (défaut `127.0.0.1`) et `TAMAGOCHAT_PORT` (défaut `8090`), ou dans un fichier
`server/.env` (voir `.env.example`, lu au démarrage, ignoré par git). Sur le VPS, nginx transmet
à `127.0.0.1:8090` : ne changer le port qu'en modifiant aussi `deploy/nginx-minou.conf`.

## Tester en local

Depuis la racine du projet :

```bash
python3 server/server.py dev        # macOS / Linux
python server\server.py dev         # Windows
```

La page http://127.0.0.1:8090/admin s'ouvre dans le navigateur ; mot de passe : `admin`.
`Ctrl + C` arrête le serveur. Au premier lancement, aiohttp est installé automatiquement dans
`server/.venv` (ignoré par git) ; les fois suivantes, le démarrage est immédiat. La page doit avoir
été compilée une fois (`cd web && npm install && npm run build`) ; pour travailler sur le front,
`npm run dev` dans `web/` lance l'API et la page ensemble (voir [web/README.md](../web/README.md)).

Le mode `dev` utilise ses propres données (`server/.dev/`, ignoré par git) avec quatre chats de
démo : deux « en ligne » reçoivent les messages et appliquent réglages, jauges et phrases, un
autre a une ancienne version (sans réglages à distance). `--reset` repart de données neuves,
`--no-browser` n'ouvre pas le navigateur, `--port 8091` change de port. Pour y relier un vrai chat :

```bash
MINOU_SERVER=http://127.0.0.1:8090 python3 chat.pyw
```

Les tests (depuis `server/`, après un premier `dev`) :

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Mettre à jour le serveur sur le VPS

Les URL, la base, `config.json` et `releases/` ne changent pas : les chats installés et
GitHub Actions continuent de fonctionner. Le service garde ses noms (`minou-server`, utilisateur
`minou`, `/opt/minou-server`). Compilez d'abord la page sur votre ordinateur
(`cd web && npm ci && npm run build`), copiez le projet sur la machine (avec `web/dist`), puis depuis
son dossier `server/` :

```bash
# 1. sauvegarde (code et données)
sudo cp -a /opt/minou-server /opt/minou-server.bak-$(date +%F)

# 2. nouveaux fichiers (les données ne sont pas touchées)
sudo cp -r server.py tamagochat_server requirements.txt /opt/minou-server/
sudo cp ../tamagochat/ed25519.py /opt/minou-server/
sudo rm -rf /opt/minou-server/web && sudo cp -r ../web/dist /opt/minou-server/web   # page admin compilée
sudo chown -R minou:minou /opt/minou-server

# 3. vérification, puis redémarrage
cd /opt/minou-server && sudo -u minou venv/bin/python server.py check
sudo systemctl restart minou-server && systemctl status minou-server --no-pager
```

`check` doit afficher `OK` (sinon, ne pas redémarrer). En cas de problème après le redémarrage,
l'ancien serveur repart tel quel avec les données actuelles (il ignore `tamagochat_server/` et `web/`) :

```bash
sudo cp /opt/minou-server.bak-AAAA-MM-JJ/server.py /opt/minou-server/
sudo systemctl restart minou-server
```

Une fois la nouvelle version validée, l'ancien `admin.html` de `/opt/minou-server/` peut être supprimé.
