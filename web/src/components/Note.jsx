export const Note = ({ icon, warn, children }) => (
  <div class={"note" + (warn ? " warn" : "")}>
    <span>{icon}</span>
    <span>{children}</span>
  </div>
);
