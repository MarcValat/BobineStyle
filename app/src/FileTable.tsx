import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { DropZone } from "./DropZone";
import { fileName, type FileItem } from "./shared";

/** One row per file: its French tracks, the fonts it gets, where it stands. */
export default function FileTable({
  files,
  selected,
  running,
  force,
  onSelect,
  onRemove,
  onAdd,
}: {
  files: FileItem[];
  selected: string | null;
  running: boolean;
  force: boolean;
  onSelect: (path: string) => void;
  onRemove: (path: string) => void;
  /** Picks files to add (the header's "+ Ajouter", the empty zone). */
  onAdd: () => void;
}) {
  return (
    <table>
      <colgroup>
        <col className="col-index" />
        <col />
        <col className="col-french" />
        <col className="col-fonts" />
        <col className="col-state" />
        <col className="col-remove" />
      </colgroup>
      <thead>
        <tr>
          <th className="index-cell">#</th>
          <th>
            <div className="th-add">
              <span>Fichier</span>
              <button className="small-button" onClick={onAdd} disabled={running} title="Ajouter des MKV">
                + Ajouter
              </button>
            </div>
          </th>
          <th>Sous-titres français</th>
          <th>Polices</th>
          <th>État</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {/* Always shown, even empty: its header holds the button that adds files. */}
        {files.length === 0 && (
          <tr className="empty-row">
            <td colSpan={6}>
              <DropZone title="Glisse des fichiers ou des dossiers ici" onClick={onAdd} disabled={running}>
                Des MKV, ou le dossier d'une saison ou d'une série : leurs sous-titres français prendront le style maison.
              </DropZone>
            </td>
          </tr>
        )}
        {files.map((f, i) => (
          <tr
            key={f.path}
            className={`${f.path === selected ? "selected" : ""} ${f.status === "no_french" ? "dim" : ""}`}
            onClick={() => onSelect(f.path)}
          >
            <td className="index-cell">{i + 1}</td>
            <td className="file-name-cell" title={f.path}>
              {fileName(f.path)}
            </td>
            <td>{frenchSummary(f)}</td>
            <td>{f.plan ? (f.plan.fonts.length > 0 ? f.plan.fonts.length : "—") : ""}</td>
            <td>
              <StatusCell file={f} force={force} />
            </td>
            <td className="remove-cell">
              {!running && (
                <button
                  className="small-button"
                  title="Retirer de la liste"
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(f.path);
                  }}
                >
                  ✕
                </button>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function frenchSummary(file: FileItem): string {
  const french = file.plan?.tracks.filter((t) => t.french) ?? [];
  if (!file.plan) return "";
  if (french.length === 0) return "—";
  return french.map((t) => (t.kind === "forced" ? "forcés" : "complets") + (t.action === "convert" ? " (SRT)" : "")).join(" + ");
}

function StatusCell({ file, force }: { file: FileItem; force: boolean }) {
  switch (file.status) {
    case "planning":
      return <span className="muted">Lecture…</span>;
    case "no_french":
      return <span className="muted">Rien à faire</span>;
    case "plan_error":
    case "error":
      return (
        <span className="error-text" title={file.error}>
          {file.status === "error" ? "Échec" : "Illisible"}
        </span>
      );
    case "queued":
      return <span className="muted">En attente</span>;
    case "running":
      return (
        <div className="progress" title={`${Math.round((file.progress ?? 0) * 100)} %`}>
          <div className="progress-bar" style={{ width: `${(file.progress ?? 0) * 100}%` }} />
        </div>
      );
    case "done":
      return (
        <span className="done-cell">
          <span className="success-text">Terminé</span>
          {file.output && (
            <button
              className="link"
              onClick={(e) => {
                e.stopPropagation();
                revealItemInDir(file.output!.path);
              }}
            >
              Afficher
            </button>
          )}
        </span>
      );
    case "cancelled":
      return <span className="muted">Annulé</span>;
    default:
      return file.output?.exists && !force ? <span className="tag">Déjà traité</span> : <span>Prêt</span>;
  }
}
