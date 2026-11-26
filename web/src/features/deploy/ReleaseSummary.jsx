export function ReleaseSummary({ d, cats }) {
  const rel = d.release;
  if (!rel) {
    return (
      <section>
        <h3>Version publiée</h3>
        <div class="relinfo">Aucune version publiée pour l'instant.</div>
      </section>
    );
  }
  const upToDate = cats.filter((c) => c.version === rel.version).length;
  const origin = rel.commit ? `compilée par GitHub (commit ${rel.commit.slice(0, 7)})` : "publiée depuis le PC";
  const date = rel.date
    ? "le " + new Date(rel.date).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) + " · "
    : "";
  return (
    <section>
      <h3>Version publiée</h3>
      <div class="relinfo">
        <div>v{rel.version}</div>
        <div class="sub">{date}{origin} · {upToDate}/{cats.length} chat(s) à jour</div>
        <div class="sub">{d.release_mac ? `Mac : v${d.release_mac.version}` : "Mac : aucune version publiée"}</div>
      </div>
    </section>
  );
}
