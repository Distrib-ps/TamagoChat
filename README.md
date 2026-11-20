# TamagoChat, le chat du bureau

Un chat tamagotchi en pixel art (il s'appelle Minou par défaut, renommable) qui vit au-dessus de la barre
des tâches de Windows. On le caresse, on le nourrit, il parle, chasse les mouches, pique des crises de folie...
et, si on le souhaite, on peut lui envoyer des messages et des bêtises à distance depuis une page web.

**Windows uniquement** (10 / 11, un ou plusieurs écrans).

## Utilisation

- **Clic gauche** : caresse · **Glisser** : déplacer (on peut le lancer, il retombe) · **Clic droit** : menu
- Menu : manger, boire, jouer avec la pelote, sieste, crise de folie, mouches, état, renommer, phrases perso, options, quitter
- Options : promenade, fréquence des phrases spontanées (30 s à 30 min, perso, ou jamais), mode FOU,
  mouches, premier plan, démarrage avec Windows, taille
- Mouches : de temps en temps des mouches apparaissent, il les traque et bondit pour les gober
  (clic sur une mouche = l'écraser)
- Mode FOU : de temps en temps il court et saute partout sur l'écran (et d'un écran à l'autre)
- Phrases : chaque situation (faim, sieste, caresse, matin...) a ses phrases, modifiables dans « Ses phrases... »
  (`{name}` est remplacé par son nom)

Ses jauges (satiété, hydratation, bonheur, énergie) baissent avec le temps, même app fermée (plus lentement,
et sans descendre sous 15). Il ne meurt jamais, il devient juste grognon.

Sauvegarde : `%APPDATA%\ChatTamagotchi\save.json` · erreurs éventuelles : `erreurs.log` dans le même dossier.

## Lancer depuis le code

Python 3.10+ (avec tkinter, inclus dans l'installeur officiel de python.org). Aucune autre dépendance.

```powershell
pythonw chat.pyw
```

Sans `local_config.py`, le chat fonctionne entièrement hors ligne.

## Fabriquer le .exe à partager

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip install pyinstaller
$ico = "$PWD\chat.ico"
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name TamagoChat --icon $ico --add-data "$ico;." --workpath "$env:TEMP\minou-build" --specpath "$env:TEMP\minou-build" chat.pyw
```

Résultat : `dist\TamagoChat.exe` (fichier unique, rien à installer). Chaque personne a son propre chat et sa
propre sauvegarde. Si `local_config.py` existe, son contenu est intégré à l'exe.

## Messages à distance et mises à jour automatiques (optionnel)

Il faut un petit serveur Linux (un VPS suffit, ~40 Mo de RAM) avec nginx. Il sert à :

- **la page admin** `https://<ton serveur>/admin` (protégée par mot de passe), en 3 onglets :
  - *Messages & actions* : messages (signés ou non, durée de bulle réglable), soins (manger, boire, caresse,
    pluie de câlins, pelote, sieste...) et bêtises (folie XXL, nuée de mouches, grand saut, tomber du ciel,
    changer d'écran, chasser la souris, cache-cache), réponses des amis
  - *Réglages & jauges* : renommer le chat, phrases spontanées, mode FOU, mouches, promenade, premier plan,
    taille ; régler ses 4 jauges
  - *Phrases* : voir / ajouter / modifier / supprimer ses phrases par situation, les lui faire dire
- **les mises à jour automatiques** : chaque nouvelle version est signée (Ed25519) ; un chat n'installe
  qu'un exe signé par ta clé privée, même si le serveur était compromis.

Côté chat, le propriétaire garde la main dans Options : « Recevoir des messages à distance »,
« Mises à jour automatiques », « Autoriser les réglages à distance » (réglages, phrases, jauges).
Il répond avec clic droit > « Envoyer un message... ».

### 1. Clé de signature (sur ton PC, une seule fois)

Depuis le dossier du projet :

```powershell
python -c "import os, secrets, ed25519_min as e; d = os.path.expanduser('~/.minou'); os.makedirs(d, exist_ok=True); s = secrets.token_bytes(32); open(os.path.join(d, 'signing.key'), 'x').write(s.hex()); print('UPDATE_PUBKEY =', e.public_key(s).hex())"
```

La clé privée est écrite dans `~\.minou\signing.key` : **ne la partage jamais et sauvegarde-la**
(la perdre empêche de publier des mises à jour : il faudrait redistribuer un exe à la main).
Garde la ligne `UPDATE_PUBKEY = ...` affichée pour l'étape 3.

### 2. Serveur (Ubuntu / Debian)

Pas de nom de domaine ? `sslip.io` en fournit un gratuit à partir de l'IP : `1.2.3.4` → `1-2-3-4.sslip.io`.
Copie le dossier `serveur/` du projet sur le serveur, place-toi dedans, puis (en remplaçant `MON-DOMAINE`
et `MOT-DE-PASSE`) :

```bash
sudo apt install -y python3-venv nginx certbot
sudo useradd --system --home /opt/minou-server --shell /usr/sbin/nologin minou
sudo mkdir -p /opt/minou-server /var/www/minou-acme
sudo cp server.py admin.html requirements.txt /opt/minou-server/
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

### 3. Configuration locale (sur ton PC)

Copie `local_config.example.py` en `local_config.py` (ignoré par git) et remplis-le :
adresse du serveur, `UPDATE_PUBKEY` de l'étape 1, et l'accès SSH utilisé pour publier (ex. `root@1.2.3.4`).
Puis fabrique l'exe (voir plus haut) et donne-le à tes amis : leurs chats apparaissent dans la page admin.

### 4. Publier une nouvelle version

Prérequis : le `.venv` avec PyInstaller (voir plus haut), [Git pour Windows](https://git-scm.com/)
(son `ssh` / `scp` est utilisé), et un accès SSH par clé au serveur (en root, ou un utilisateur pouvant
écrire dans `/opt/minou-server/releases` et faire `chown`).

```powershell
.\publier.ps1          # version suivante (1.0.0 -> 1.0.1)
.\publier.ps1 1.2.0    # version précise
```

Le script change `APP_VERSION` dans `chat.pyw`, compile `dist\TamagoChat.exe`, le signe et l'envoie :
tous les chats connectés se mettent à jour seuls en moins d'une minute.

## Fichiers

| Fichier | Rôle |
|---|---|
| `chat.pyw` | l'application (tkinter) |
| `sprites.py` | les dessins en pixel art |
| `ed25519_min.py` | signatures Ed25519 en Python pur (vérification des mises à jour) |
| `local_config.example.py` | modèle de configuration privée |
| `publier.py`, `publier.ps1` | compilation, signature et envoi d'une nouvelle version |
| `serveur/server.py` | serveur aiohttp + SQLite (API des chats, page admin, téléchargements) |
| `serveur/admin.html` | la page admin |
| `serveur/minou-server.service`, `serveur/nginx-minou.conf` | service systemd et site nginx |
