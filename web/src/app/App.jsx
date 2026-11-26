import { useEffect, useState } from "preact/hooks";
import { Toasts } from "../components/Toasts.jsx";
import { LoginPage } from "../features/auth/LoginPage.jsx";
import { api, quiet, setUnauthorizedHandler } from "../lib/api.js";
import { usePolling } from "../lib/hooks.js";
import { Dashboard } from "./Dashboard.jsx";

export function App() {
  const [authed, setAuthed] = useState(null);     // null : on ne sait pas encore
  const [data, setData] = useState(null);

  const refresh = () => api("/admin/api/state").then((s) => { setData(s); setAuthed(true); }).catch(quiet);
  useEffect(() => { setUnauthorizedHandler(() => setAuthed(false)); }, []);
  usePolling(() => { if (authed !== false) refresh(); }, 3000, [authed]);

  const logout = async () => {
    await api("/admin/api/logout", {}).catch(() => {});
    setAuthed(false);
  };

  return (
    <>
      {authed === false && <LoginPage onLogin={refresh} />}
      {authed && data && <Dashboard data={data} refresh={refresh} onLogout={logout} />}
      <Toasts />
    </>
  );
}
