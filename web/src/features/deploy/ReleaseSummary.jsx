import { PanelTitle } from "../../components/ui.jsx";

export function ReleaseSummary({ d, cats }) {
  const rel = d.release;
  if (!rel) {
    return (
      <section class="grid gap-2">
        <PanelTitle>Version publiée</PanelTitle>
        <p class="text-ink-soft">Aucune version publiée pour l'instant.</p>
      </section>
    );
  }
  const upToDate = cats.filter((c) => c.version === rel.version).length;
  const origin = rel.commit ? `Compilée par GitHub (commit ${rel.commit.slice(0, 7)})` : "Publiée depuis le PC";
  const date = rel.date && new Date(rel.date).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
  return (
    <section class="grid gap-2">
      <PanelTitle>Version publiée</PanelTitle>
      <div class="rounded-chip border-2 border-line bg-paper-2 px-4 py-3">
        <p class="font-pixel text-2xl font-bold">{rel.version}</p>
        <p class="text-sm text-ink-soft">{origin}{date && `, le ${date}`}.</p>
        <p class="text-sm text-ink-soft">
          {upToDate} chat{upToDate > 1 ? "s" : ""} sur {cats.length} à jour.{" "}
          {d.release_mac ? `Version Mac : ${d.release_mac.version}.` : "Aucune version Mac publiée."}
        </p>
      </div>
    </section>
  );
}
