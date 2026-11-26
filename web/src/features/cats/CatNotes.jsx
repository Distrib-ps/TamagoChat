import { Note } from "../../components/Note.jsx";

export const OldVersionNote = ({ cat }) => (
  <section class="pane">
    <Note icon="⏳">
      {cat.name} a encore une ancienne version (v{cat.version || "?"}). Cette partie arrive avec la v1.1 : il se
      mettra à jour tout seul dès qu'il sera allumé.
    </Note>
  </section>
);

export function RemoteStatusNote({ cat }) {
  if (cat.allow_settings === false) {
    return (
      <Note icon="🔒" warn>
        {cat.name} a désactivé « Autoriser les réglages à distance » de son côté : tes changements ne seront pas appliqués.
      </Note>
    );
  }
  if (!cat.online) {
    return <Note icon="💤">{cat.name} est hors ligne : les changements seront appliqués à sa prochaine connexion.</Note>;
  }
  return null;
}
