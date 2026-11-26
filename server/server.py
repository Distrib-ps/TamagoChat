"""Point d'entrée du serveur, lancé par systemd : python server.py --help."""
from tamagochat_server.cli import main

if __name__ == "__main__":
    main()
