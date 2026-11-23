# Copie ce fichier en local_config.py (jamais versionné) et remplis-le.
# Sans local_config.py, le chat fonctionne normalement mais sans messages ni mises à jour à distance.
# (Les versions publiées par GitHub Actions le génèrent à partir des variables du dépôt.)

# Adresse HTTPS du serveur (dossier serveur/), sans / final. Ex. : "https://1-2-3-4.sslip.io"
SERVER_URL = ""

# Clé publique Ed25519 (64 caractères hexa) qui vérifie les mises à jour.
# Pour créer la paire de clés : voir « Clé de signature » dans le README.
UPDATE_PUBKEY = ""
