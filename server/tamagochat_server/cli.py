import argparse
import asyncio
import importlib.util
import os
import re
import shutil
import subprocess
import sys

from .settings import DEV_DATA_DIR, HOST, PORT, SERVER_DIR, WEB_DIR

WEB_FILES = ("index.html", "favicon.ico", "images/cat.png")
DEV_VENV = os.path.join(SERVER_DIR, ".venv")


def use_dev_environment():
    """Test local : si aiohttp manque, l'installe une fois dans server/.venv et relance la
    commande avec ce Python. Rien à préparer à la main."""
    if importlib.util.find_spec("aiohttp"):
        return
    in_venv = os.path.abspath(sys.prefix) == os.path.abspath(DEV_VENV)
    python = sys.executable if in_venv else os.path.join(
        DEV_VENV, "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
    if in_venv or not os.path.exists(python):
        print("Premier lancement : installation d'aiohttp dans server/.venv (une seule fois)…", flush=True)
        if not in_venv:
            subprocess.check_call([sys.executable, "-m", "venv", DEV_VENV])
        subprocess.check_call([python, "-m", "pip", "install", "-q", "--disable-pip-version-check",
                               "-r", os.path.join(SERVER_DIR, "requirements.txt")])
    if in_venv:
        return
    command = [python, os.path.join(SERVER_DIR, "server.py"), *sys.argv[1:]]
    if os.name != "nt":
        os.execv(python, command)          # remplace ce processus : un seul serveur à arrêter
    try:
        sys.exit(subprocess.call(command))
    except KeyboardInterrupt:
        sys.exit(0)


def serve(data_dir, port=PORT, dev=False, page=True, browser=False):
    from aiohttp import web

    from . import demo
    from .app import Services, create_app

    svc = Services(data_dir, secure_cookies=not dev)
    app = create_app(svc)
    if dev:
        if not svc.auth.has_password():
            svc.auth.set_password(demo.PASSWORD)
        demo.seed(svc)

        async def simulation(app):
            task = asyncio.ensure_future(demo.simulate(svc))
            yield
            task.cancel()
        app.cleanup_ctx.append(simulation)
        url = f"http://{HOST}:{port}/admin"
        if page and not os.path.isfile(os.path.join(WEB_DIR, "index.html")):
            print("La page admin n'est pas encore compilée. Pour développer le front : cd web && npm install "
                  "&& npm run dev ; pour l'avoir ici : cd web && npm run build")
            browser = False
        if not page:
            url = f"http://{HOST}:{port} (API)"
        if browser:
            async def open_browser(app):
                import webbrowser
                asyncio.get_running_loop().call_later(0.5, webbrowser.open, url)
            app.on_startup.append(open_browser)
        print(f"TamagoChat (test local) : {url} · mot de passe : {demo.PASSWORD} · Ctrl+C pour arrêter")
        print(f"Relier un vrai chat : MINOU_SERVER=http://{HOST}:{port} python3 chat.pyw")
    web.run_app(app, host=HOST, port=port, access_log=None, print=None)


def check(data_dir):
    if hasattr(os, "geteuid") and os.geteuid() == 0 and os.stat(data_dir).st_uid != 0:
        # root créerait des fichiers (minou.db-wal…) que le service ne pourrait plus écrire
        sys.exit("À lancer avec l'utilisateur du service : sudo -u minou venv/bin/python server.py check")
    problems = []
    try:
        import aiohttp

        from .app import Services, create_app
        from .services.signing import ed25519

        print(f"Python {sys.version.split()[0]} · aiohttp {aiohttp.__version__}")
        svc = Services(data_dir)
        create_app(svc)
        cats = len(svc.cats.ids())
        win, mac = svc.releases.latest("win"), svc.releases.latest("mac")
        print(f"Base : {cats} chat(s) · version Windows {win['version'] if win else '-'}"
              f" · version Mac {mac['version'] if mac else '-'}")
        problems += [f"page admin incomplète : {os.path.join(WEB_DIR, f)} manque (cd web && npm run build)"
                     for f in WEB_FILES if not os.path.isfile(os.path.join(WEB_DIR, f))]
        if not svc.auth.has_password():
            problems.append("pas de mot de passe admin (server.py set-password ...)")
        if svc.config.get("deploy_hash"):
            ed25519()
        svc.close()
    except Exception as e:
        problems.append(f"{type(e).__name__} : {e}")
    for p in problems:
        print("PROBLÈME :", p)
    print("OK" if not problems else "À corriger avant de redémarrer.")
    return not problems


def main():
    parser = argparse.ArgumentParser(prog="server.py", description="Serveur TamagoChat")
    sub = parser.add_subparsers(dest="command", metavar="commande")
    dev = sub.add_parser("dev", help="test local avec des chats de démo")
    dev.add_argument("--port", type=int, default=PORT)
    dev.add_argument("--reset", action="store_true", help="repartir de données de démo neuves")
    dev.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    dev.add_argument("--api-only", action="store_true", help="seulement l'API (lancé par npm run dev dans web/)")
    sub.add_parser("check", help="vérifier l'installation avant de redémarrer")
    pw = sub.add_parser("set-password", help="changer le mot de passe admin")
    pw.add_argument("password")
    sd = sub.add_parser("setup-deploy", help="activer la publication depuis GitHub Actions")
    sd.add_argument("repo", help="PROPRIETAIRE/DEPOT")
    sd.add_argument("pubkey", help="clé publique de signature (hex)")
    args = parser.parse_args()

    if args.command == "dev":
        use_dev_environment()
        if args.reset:
            shutil.rmtree(DEV_DATA_DIR, ignore_errors=True)
        os.makedirs(DEV_DATA_DIR, exist_ok=True)
        try:
            serve(DEV_DATA_DIR, args.port, dev=True, page=not args.api_only,
                  browser=not (args.no_browser or args.api_only))
        except OSError as e:
            sys.exit(f"Impossible de démarrer sur le port {args.port} ({e.strerror}) : "
                     f"un serveur tourne déjà ? Sinon : --port 8091")
    elif args.command == "check":
        sys.exit(0 if check(SERVER_DIR) else 1)
    elif args.command == "set-password":
        from .app import Services
        Services(SERVER_DIR).auth.set_password(args.password)
        print("Mot de passe admin mis à jour.")
    elif args.command == "setup-deploy":
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo) or not re.fullmatch(r"[0-9a-f]{64}", args.pubkey):
            sys.exit("usage : server.py setup-deploy PROPRIETAIRE/DEPOT CLE_PUBLIQUE_HEX")
        from .app import Services
        print(Services(SERVER_DIR).auth.create_deploy_token(args.repo, args.pubkey))
    else:
        serve(SERVER_DIR)
