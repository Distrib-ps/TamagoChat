import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import preact from "@preact/preset-vite";
import { defineConfig, loadEnv } from "vite";

const SERVER = fileURLToPath(new URL("../server/server.py", import.meta.url));

// `npm run dev` lance aussi l'API Python, sauf si elle tourne déjà. Elle survit aux redémarrages
// de Vite (modification de ce fichier ou du .env) et s'arrête avec lui.
function startApi(url, port) {
  return {
    name: "tamagochat-api",
    apply: "serve",
    async configureServer(server) {
      if (await fetch(`${url}/api/latest`).then(() => true, () => false)) return;
      const python = process.platform === "win32" ? "python" : "python3";
      const api = spawn(python, [SERVER, "dev", "--api-only", "--port", port], { stdio: "inherit" });
      api.on("error", (e) => server.config.logger.error(`API non lancée (${python} introuvable ?) : ${e.message}`));
      process.once("exit", () => api.kill());
    },
  };
}

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiPort = env.API_PORT || "8090";
  const api = `http://127.0.0.1:${apiPort}`;
  return {
    base: command === "build" ? "/admin/static/" : "/",
    plugins: [preact(), startApi(api, apiPort)],
    server: { port: Number(env.WEB_PORT || 5173), open: true, proxy: { "/admin/api": api } },
    build: { outDir: "dist", emptyOutDir: true },
  };
});
