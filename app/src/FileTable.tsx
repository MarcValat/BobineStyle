import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { DropZone } from "./DropZone";
import { FolderIcon, RedoIcon } from "./icons";
import { fileName, type FileItem, isRedoable } from "./shared";

/** One row per file: its French tracks, the fonts it gets, where it stands
 * (a bar at its left, as Bobine Audio's and Bobine Subs' rows), and its
 * buttons: redo it, open the folder it was written to, take it off. */
export default function FileTable({
  files,
  selected,
  running,
  force,
  onSelect,
  onRemove,
  onAdd,
  onRedo,
}: {
  files: FileItem[];
  selected: string | null;
  running: boolean;
  force: boolean;
  onSelect: (path: string) => void;
  onRemove: (path: string) => void;
  /** Picks files to add (the header's "+ Ajouter", the empty zone). */
  onAdd: () => void;
  /** Processes this one file again, even if its output exists. */
  onRedo: (path: string) => void;
}) {
  return (
    <table>
      <colgroup>
        <col className="col-index" />
        <col />
        <col className="col-french" />
        <col className="col-fonts" />
        <col className="col-state" />
        <col className="col-icon" />
        <col className="col-icon" />
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
          <th />
        </tr>
      </thead>
      <tbody>
        {/* Always shown, even empty: its header holds the button that adds files. */}
        {files.length === 0 && (
          <tr className="empty-row">
            <td colSpan={7}>
              <DropZone title="Glisse des fichiers ou des dossiers ici" onClick={onAdd} disabled={running}>
                Des MKV, ou le dossier d'une saison ou d'une série : leurs sous-titres français prendront le style maison.
              </DropZone>
            </td>
          </tr>
        )}
        {files.map((f, i) => (
          <tr
            key={f.path}
            className={`row-state-${rowState(f, force)}${f.path === selected ? " selected" : ""}${f.status === "no_french" ? " dim" : ""}`}
            onClick={() => onSelect(f.path)}
          >
            <td className="index-cell">{i + 1}</td>
            <td className="file-name-cell" title={f.path}>
              {fileName(f.path)}
            </td>
            <td>{frenchSummary(f)}</td>
            <td>{f.plan ? (f.plan.fonts.length > 0 ? f.plan.fonts.length : "—") : ""}</td>
            <td>
              <div className="state-cell">
                <span className="state-text">
                  <StatusText file={f} force={force} />
                </span>
                {!running && isRedoable(f) && f.output?.exists && (
                  <button
                    className="small-button icon-small-button"
                    title="Refaire ce fichier"
                    aria-label="Refaire ce fichier"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRedo(f.path);
                    }}
                  >
                    <RedoIcon />
                  </button>
                )}
              </div>
            </td>
            <td className="icon-cell">
              {f.output?.exists && f.status !== "running" && f.status !== "no_french" && (
                <button
                  className="small-button icon-small-button"
                  title="Ouvrir le dossier du fichier écrit"
                  aria-label="Ouvrir le dossier du fichier écrit"
                  onClick={(e) => {
                    e.stopPropagation();
                    revealItemInDir(f.output!.path);
                  }}
                >
                  <FolderIcon />
                </button>
              )}
            </td>
            <td className="icon-cell">
              {!running && (
                <button
                  className="small-button icon-small-button"
                  title="Retirer de la liste"
                  aria-label="Retirer de la liste"
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

/** The bar at a row's left: running, waiting (or being read), ready, done
 * (or already done), failed; none when there's nothing to do. */
function rowState(file: FileItem, force: boolean): string {
  switch (file.status) {
    case "running":
      return "running";
    case "queued":
    case "planning":
      return "queued";
    case "done":
      return "done";
    case "error":
    case "plan_error":
      return "error";
    case "ready":
      return file.output?.exists && !force ? "done" : "ready";
    default:
      return "idle";
  }
}

function frenchSummary(file: FileItem): string {
  const french = file.plan?.tracks.filter((t) => t.french) ?? [];
  if (!file.plan) return "";
  if (french.length === 0) return "—";
  return french.map((t) => (t.kind === "forced" ? "forcés" : "complets") + (t.action === "convert" ? " (SRT)" : "")).join(" + ");
}

function StatusText({ file, force }: { file: FileItem; force: boolean }) {
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
      return <span className="success-text">Terminé</span>;
    case "cancelled":
      return <span className="muted">Annulé</span>;
    default:
      return file.output?.exists && !force ? <span className="tag">Déjà traité</span> : <span>Prêt</span>;
  }
}
