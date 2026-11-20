# Copie ce fichier en local_config.py (jamais versionné) et remplis-le.
# Sans local_config.py, le chat fonctionne normalement mais sans messages ni mises à jour à distance.

# Adresse HTTPS du serveur (dossier serveur/), sans / final. Ex. : "https://1-2-3-4.sslip.io"
SERVER_URL = ""

# Clé publique Ed25519 (64 caractères hexa) qui vérifie les mises à jour.
# La clé privée correspondante reste dans ~/.minou/signing.key et ne doit jamais être partagée.
# Pour créer la paire de clés : voir « 1. Clé de signature » dans le README.
UPDATE_PUBKEY = ""

# Accès SSH au serveur, utilisé par publier.py. Ex. : "root@1.2.3.4"
VPS = ""
