import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { DropZone } from "./DropZone";
import { useT } from "./i18n";
import type { Messages } from "./i18n/fr";
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
  const t = useT();
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
              <span>{t.list.file}</span>
              <button className="small-button" onClick={onAdd} disabled={running} title={t.add.files}>
                {t.common.add}
              </button>
            </div>
          </th>
          <th>{t.list.french}</th>
          <th>{t.list.fonts}</th>
          <th>{t.list.state}</th>
          <th />
          <th />
        </tr>
      </thead>
      <tbody>
        {/* Always shown, even empty: its header holds the button that adds files. */}
        {files.length === 0 && (
          <tr className="empty-row">
            <td colSpan={7}>
              <DropZone title={t.list.emptyTitle} onClick={onAdd} disabled={running}>
                {t.list.emptyHint}
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
            <td>{frenchSummary(f, t)}</td>
            <td>{f.plan ? (f.plan.fonts.length > 0 ? f.plan.fonts.length : "—") : ""}</td>
            <td>
              <div className="state-cell">
                <span className="state-text">
                  <StatusText file={f} force={force} />
                </span>
                {!running && isRedoable(f) && f.output?.exists && (
                  <button
                    className="small-button icon-small-button"
                    title={t.list.redo}
                    aria-label={t.list.redo}
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
                  title={t.list.openFolder}
                  aria-label={t.list.openFolder}
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
                  title={t.list.remove}
                  aria-label={t.list.remove}
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

function frenchSummary(file: FileItem, t: Messages): string {
  const french = file.plan?.tracks.filter((track) => track.french) ?? [];
  if (!file.plan) return "";
  if (french.length === 0) return "—";
  return french
    .map((track) => (track.kind === "forced" ? t.list.forced : t.list.full) + (track.action === "convert" ? " (SRT)" : ""))
    .join(" + ");
}

function StatusText({ file, force }: { file: FileItem; force: boolean }) {
  const t = useT();
  switch (file.status) {
    case "planning":
      return <span className="muted">{t.status.reading}</span>;
    case "no_french":
      return <span className="muted">{t.status.nothingToDo}</span>;
    case "plan_error":
    case "error":
      return (
        <span className="error-text" title={file.error}>
          {file.status === "error" ? t.status.failed : t.status.unreadable}
        </span>
      );
    case "queued":
      return <span className="muted">{t.status.waiting}</span>;
    case "running":
      return (
        <div className="progress" title={t.status.percent(Math.round((file.progress ?? 0) * 100))}>
          <div className="progress-bar" style={{ width: `${(file.progress ?? 0) * 100}%` }} />
        </div>
      );
    case "done":
      return <span className="success-text">{t.status.done}</span>;
    case "cancelled":
      return <span className="muted">{t.common.cancelled}</span>;
    default:
      return file.output?.exists && !force ? <span className="tag">{t.status.alreadyDone}</span> : <span>{t.status.ready}</span>;
  }
}
