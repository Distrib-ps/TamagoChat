# TamagoChat, le chat du bureau

Un chat tamagotchi en pixel art (il s'appelle Minou par défaut, renommable) qui vit au-dessus de la barre
des tâches (Windows) ou du Dock (Mac). On le caresse, on le nourrit, il parle, chasse les mouches, pique
des crises de folie... et on peut lui envoyer des messages et des bêtises à distance depuis une page web.

**Windows 10 / 11 et macOS**, un ou plusieurs écrans.

## Installer

Télécharge la dernière version sur la page
[Releases](https://github.com/Distrib-ps/TamagoChat/releases/latest) :

- **Windows** : `TamagoChat-x.y.z.exe`, à lancer directement (rien à installer).
- **Mac** : `TamagoChat-x.y.z-mac.zip`, à décompresser, puis glisser `TamagoChat` dans **Applications**.
  La première fois, fais clic droit > **Ouvrir** (l'app n'est pas signée par Apple).

Ensuite, il se met à jour tout seul.

## Utilisation

- **Clic gauche** : caresse · **Glisser** : déplacer (on peut le lancer, il retombe)
- **Clic droit** (ou ctrl+clic sur Mac) : menu (manger, boire, pelote, sieste, crise de folie, mouches,
  état, renommer, phrases perso, options, quitter)
- Options : promenade, fréquence des phrases spontanées, mode FOU, mouches, premier plan, lancement au
  démarrage, taille
- Mouches : de temps en temps des mouches apparaissent, il les traque et bondit pour les gober
  (clic sur une mouche = l'écraser)
- Phrases : chaque situation (faim, sieste, caresse, matin...) a ses phrases, modifiables dans
  « Ses phrases... » (`{name}` est remplacé par son nom)

Ses jauges (satiété, hydratation, bonheur, énergie) baissent avec le temps, même app fermée (plus
lentement, et sans descendre sous 15). Il ne meurt jamais, il devient juste grognon.

Sauvegarde et erreurs éventuelles (`save.json`, `erreurs.log`) :
`%APPDATA%\ChatTamagotchi` sur Windows, `~/Library/Application Support/ChatTamagotchi` sur Mac.

## Lancer depuis le code

Python 3.10+ de [python.org](https://www.python.org/downloads/), aucune autre dépendance. Depuis le dossier
du projet :

```bash
python3 chat.pyw       # Mac
python chat.pyw        # Windows (ou un double-clic sur chat.pyw)
```

Sur Mac, prends bien le Python de python.org : celui de Homebrew utilise Tk 9, qui n'affiche pas les
fenêtres transparentes (le chat te le signale au lancement).

Sans `local_config.py`, le chat fonctionne entièrement hors ligne.

### Organisation du code

| Fichier | Rôle |
|---|---|
| `chat.pyw` | lanceur (Windows et Mac) |
| `tamagochat/app.py` | l'application : fenêtre, boucle principale, souris, écrans, sauvegarde |
| `tamagochat/behavior.py` | comportement autonome : jauges, paroles, décisions, états |
| `tamagochat/actions.py` | soins, jeux et pouvoirs envoyés depuis la page admin |
| `tamagochat/hunt.py`, `fly.py` | chasse aux mouches |
| `tamagochat/render.py`, `sprites.py` | dessin en pixel art |
| `tamagochat/bubble.py` | bulle de dialogue |
| `tamagochat/menu.py`, `dialogs.py` | menu du clic droit et fenêtres annexes |
| `tamagochat/remote.py` | lien avec le serveur et mises à jour signées |
| `tamagochat/desktop/` | ce qui dépend du système : `windows.py` et `macos.py`, même interface |
| `tamagochat/config.py`, `phrases.py`, `storage.py` | réglages, phrases, sauvegarde |
| `tamagochat/ed25519.py` | signatures Ed25519 en Python pur |
| `tests/` | tests (`python -m unittest discover -s tests`) |
| `serveur/` | serveur aiohttp + SQLite, page admin, service systemd et site nginx |

## Publier une nouvelle version

Clique sur le bouton **🚀** de la page admin (en haut à droite). La fenêtre montre la version publiée,
les changements pas encore déployés et le numéro de la prochaine version, puis lance la publication en
un clic (ou depuis l'onglet *Actions* de GitHub, workflow « Publier une version »).

Le numéro est calculé par [semantic-release](https://semantic-release.org) d'après les messages de commit
([Conventional Commits](https://www.conventionalcommits.org/fr/)) :

| Message de commit | Nouvelle version |
|---|---|
| `fix: le chat ne tombe plus de l'écran` | 1.1.2 → 1.1.3 |
| `feat: nouvelle bêtise « danse »` | 1.1.2 → 1.2.0 |
| `feat!: ...` ou `BREAKING CHANGE:` dans le corps | 1.1.2 → 2.0.0 |
| `chore: ...`, `docs: ...`, `refactor: ...` | rien à publier |

GitHub Actions lance les tests, compile l'app Windows et Mac (~5 min), les signe et les envoie au
serveur, puis crée le tag, `CHANGELOG.md` et la release GitHub (avec les deux fichiers à télécharger).
Tous les chats connectés se mettent à jour dans la minute.

## Messages à distance et mises à jour automatiques (mise en place, une seule fois)

Il faut un petit serveur Linux (un VPS suffit, ~40 Mo de RAM) avec nginx. Il sert :

- **la page admin** `https://<ton serveur>/admin` (protégée par mot de passe) : messages, soins et bêtises
  (folie XXL, nuée de mouches, grand saut, tomber du ciel, changer d'écran, chasser la souris,
  cache-cache), réglages et jauges, phrases, réponses des amis ;
- **les mises à jour** : chaque version est signée (Ed25519) ; un chat n'installe qu'une version signée
  par ta clé privée, même si le serveur était compromis.

Côté chat, le propriétaire garde la main dans Options : « Recevoir des messages à distance »,
« Mises à jour automatiques », « Autoriser les réglages à distance ». Il répond avec clic droit >
« Envoyer un message... ».

### 1. Clé de signature

Depuis le dossier du projet :

```bash
python -c "import secrets; from tamagochat import ed25519; s = secrets.token_bytes(32); print('SIGNING_KEY   =', s.hex()); print('UPDATE_PUBKEY =', ed25519.public_key(s).hex())"
```

Garde `SIGNING_KEY` secrète et sauvegardée : la perdre empêche de publier des mises à jour.

**Tu as déjà une clé** (`~/.minou/signing.key`, déjà dans le secret GitHub `SIGNING_KEY`) ? Garde-la :
les chats déjà installés ne font confiance qu'à elle.

### 2. Installer le serveur (Ubuntu / Debian)

Pas de nom de domaine ? `sslip.io` en fournit un gratuit à partir de l'IP : `1.2.3.4` → `1-2-3-4.sslip.io`.
Copie le dossier `serveur/` du projet sur le serveur, place-toi dedans, puis (en remplaçant `MON-DOMAINE`
et `MOT-DE-PASSE`) :

```bash
sudo apt install -y python3-venv nginx certbot
sudo useradd --system --home /opt/minou-server --shell /usr/sbin/nologin minou
sudo mkdir -p /opt/minou-server /var/www/minou-acme
sudo cp server.py admin.html requirements.txt ../tamagochat/ed25519.py /opt/minou-server/
sudo cp minou-server.service /etc/systemd/system/
sed 's/TON-DOMAINE/MON-DOMAINE/g' nginx-minou.conf | sudo tee /etc/nginx/sites-available/minou > /dev/null

cd /opt/minou-server
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
sudo chown -R minou:minou /opt/minou-server
sudo -u minou venv/bin/python server.py set-password 'MOT-DE-PASSE'

# service (n'écoute qu'en local, sur 127.0.0.1:8090)
sudo systemctl daemon-reload && sudo systemctl enable --now minou-server

# nginx en HTTP, certificat Let's Encrypt, puis activation du HTTPS
sudo ln -s /etc/nginx/sites-available/minou /etc/nginx/sites-enabled/minou
sudo nginx -t && sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/minou-acme -d MON-DOMAINE --deploy-hook "systemctl reload nginx"
sudo sed -i 's/^#SSL#//' /etc/nginx/sites-available/minou
sudo nginx -t && sudo systemctl reload nginx
```

La page `https://MON-DOMAINE/admin` doit maintenant s'ouvrir. Données : `/opt/minou-server/minou.db`.
Changer le mot de passe plus tard : relancer la commande `set-password` (déconnecte les sessions ouvertes).


Pour mettre le serveur à jour plus tard : recopie `server.py`, `admin.html` et `../tamagochat/ed25519.py`
dans `/opt/minou-server/` (et `nginx-minou.conf` s'il a changé), puis `sudo systemctl restart minou-server`.

### 3. Déploiement depuis GitHub

GitHub n'a **aucun accès SSH** au serveur : il envoie chaque version à `/api/release` avec un jeton dédié,
et le serveur revérifie la signature avant de la publier.

1. Sur le serveur, active le déploiement ; la commande affiche un jeton :
   `cd /opt/minou-server && sudo -u minou venv/bin/python server.py setup-deploy PROPRIETAIRE/DEPOT CLE_PUBLIQUE`
2. Dans le dépôt GitHub (*Settings > Secrets and variables > Actions*) :
   - secrets `SIGNING_KEY` (la clé privée, étape 1), `SERVER_URL` (ex. `https://1-2-3-4.sslip.io`) et
     `DEPLOY_TOKEN` (le jeton ci-dessus) ;
   - variable `UPDATE_PUBKEY` (la clé publique).
3. Crée un token GitHub *fine-grained* limité à ce dépôt (permissions : Actions en lecture/écriture,
   Contents en lecture) et colle-le dans la fenêtre 🚀 de la page admin.

> La clé de signature est stockée dans les secrets GitHub : protège le compte propriétaire du dépôt
> (double authentification), car il permet de publier une mise à jour.

Si `main` est protégée, autorise GitHub Actions à y pousser : semantic-release y commite la version et
le `CHANGELOG.md` (commit `chore(release)`).

Pour lancer le chat depuis le code avec le serveur, copie `local_config.example.py` en `local_config.py`
et remplis-le.

## Licence

MIT, voir [LICENSE](LICENSE).
