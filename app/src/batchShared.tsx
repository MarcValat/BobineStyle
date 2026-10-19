import { useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import type { Output, Plan } from "./api";
import { Dialog, DialogHeader } from "./Dialog";
import { FolderIcon } from "./icons";
import { Tooltip } from "./InfoTip";
import { pickFolder } from "./mediaDialog";
import { Setting } from "./Options";
import { PillSwitch } from "./PillSwitch";
import { loadSetting, saveSetting } from "./util";
import { useT } from "./i18n";
import type { BadgeKind } from "./Workspace";

// The workspace's shared pieces, after Bobine Audio's batchShared.tsx: a
// file's state, the output folder, the footer.

export function moved<T>(arr: T[], from: number, to: number): T[] {
  if (to < 0 || to >= arr.length) return arr;
  const copy = [...arr];
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

/** Runs at most `n` of the functions given to it at a time, in order. */
export function limiter(n: number) {
  let active = 0;
  const queue: (() => void)[] = [];
  const next = () => {
    if (active < n && queue.length > 0) {
      active++;
      queue.shift()!();
    }
  };
  return <T,>(fn: () => Promise<T>): Promise<T> =>
    new Promise<T>((resolve, reject) => {
      queue.push(() =>
        fn()
          .then(resolve, reject)
          .finally(() => {
            active--;
            next();
          }),
      );
      next();
    });
}

/** Where one file stands, from being read to being written. */
type FileStatus =
  | "planning" // tracks being read
  | "ready" // French subtitles found, can be processed
  | "no_french" // nothing to do
  | "plan_error" // unreadable
  | "queued"
  | "running"
  | "done"
  | "error" // the remux failed
  | "cancelled";

export interface FileItem {
  path: string;
  status: FileStatus;
  plan?: Plan;
  output?: Output;
  progress?: number;
  jobId?: string;
  error?: string;
  /** Its last run's messages (the job's log). */
  log?: string[];
}

/** Has French subtitles, is read and not busy: can be processed, again too
 * (the detail's "Refaire ce fichier"). */
export function isRedoable(file: FileItem): boolean {
  return ["ready", "done", "error", "cancelled"].includes(file.status) && file.output !== undefined;
}

/** To process with the main button: redoable, its output free unless
 * `force`. */
export function isRunnable(file: FileItem, force: boolean): boolean {
  return isRedoable(file) && (force || !file.output!.exists);
}

/** Already written by an earlier run, and not to be redone. */
export function isAlreadyDone(file: FileItem, force: boolean): boolean {
  return file.status === "ready" && !!file.output?.exists && !force;
}

/** The bar at a row's left: running, waiting (or being read), ready, done
 * (or already done), failed; none when there's nothing to do. */
export function rowState(file: FileItem, force: boolean): string {
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
      return isAlreadyDone(file, force) ? "done" : "ready";
    default:
      return "idle";
  }
}

/** A row's badge: its words and its tint. */
export function useRowBadge(): (file: FileItem, force: boolean) => [string, BadgeKind] {
  const t = useT();
  return (file, force) => {
    const s = t.status;
    switch (file.status) {
      case "planning":
        return [s.reading, "idle"];
      case "no_french":
        return [s.nothingToDo, "idle"];
      case "plan_error":
        return [s.unreadable, "error"];
      case "error":
        return [s.failed, "error"];
      case "queued":
        return [s.waiting, "queued"];
      case "running":
        return [s.percent(Math.round((file.progress ?? 0) * 100)), "running"];
      case "done":
        return [s.done, "done"];
      case "cancelled":
        return [t.common.cancelled, "idle"];
      default:
        return isAlreadyDone(file, force) ? [s.alreadyDone, "done"] : [s.ready, "ready"];
    }
  };
}

const OUTPUT_DIR_KEY = "bobinestyle.outputDir";

/** The folder the processed files go to (null: an "Output" folder next to
 * each original), kept for the next session. */
export const loadOutputDir = (): string | null => loadSetting(OUTPUT_DIR_KEY);
export const saveOutputDir = (dir: string | null): void => saveSetting(OUTPUT_DIR_KEY, dir);

/** The row's folder icon, once its file is written (as in Bobine Subs). */
export function RevealButton({ file }: { file: string | undefined }) {
  const t = useT();
  if (!file) return null;
  return (
    <Tooltip text={t.list.openFolder}>
      <button className="small-button icon-small-button" aria-label={t.list.openFolder} onClick={() => revealItemInDir(file)}>
        <FolderIcon />
      </button>
    </Tooltip>
  );
}

/** "Sortie : dossier « Output » à côté des originaux · Modifier…", in the
 * footer (Bobine Audio's ExportChooser): the dialog it opens picks it. */
function OutputChooser({
  outputDir,
  onOutputDirChange,
  disabled,
}: {
  outputDir: string | null;
  onOutputDirChange: (dir: string | null) => void;
  disabled: boolean;
}) {
  const t = useT();
  const [open, setOpen] = useState(false);
  return (
    <div className="batch-output">
      <span className="batch-output-label">{t.output.label}</span>
      <span className={outputDir ? "batch-output-dir batch-output-path" : "batch-output-dir"} title={outputDir ?? undefined}>
        {outputDir ?? t.output.nextToShort}
      </span>
      <button className="small-button" disabled={disabled} title={t.output.where} onClick={() => setOpen(true)}>
        {t.output.edit}
      </button>
      {/* At the page's root: inside the footer (a .panel), it took its look. */}
      {open &&
        createPortal(
          <OutputDialog outputDir={outputDir} onOutputDirChange={onOutputDirChange} onClose={() => setOpen(false)} />,
          document.body,
        )}
    </div>
  );
}

function OutputDialog({
  outputDir,
  onOutputDirChange,
  onClose,
}: {
  outputDir: string | null;
  onOutputDirChange: (dir: string | null) => void;
  onClose: () => void;
}) {
  const t = useT();
  async function chooseFolder() {
    const dir = await pickFolder(outputDir);
    if (dir) onOutputDirChange(dir);
  }
  return (
    <Dialog onClose={onClose} closeOnBackdrop className="export-options-panel" labelledBy="output-title">
      <DialogHeader id="output-title" title={t.output.title} onClose={onClose} />
      <Setting label={t.output.where} hint={t.output.nextToHint}>
        <PillSwitch
          className="pill-switch-wide"
          label={t.output.where}
          options={[
            ["next", t.output.nextTo],
            ["folder", t.output.otherFolder],
          ]}
          value={outputDir === null ? "next" : "folder"}
          onChange={(choice) => (choice === "next" ? onOutputDirChange(null) : chooseFolder())}
        />
        <span className="export-options-folder">
          <span className={outputDir ? "batch-output-dir batch-output-path" : "batch-output-dir"} title={outputDir ?? undefined}>
            {outputDir ?? t.output.nextToText}
          </span>
          {outputDir && (
            <button className="small-button" onClick={chooseFolder}>
              {t.common.change}
            </button>
          )}
        </span>
      </Setting>
    </Dialog>
  );
}

/** The footer: where the files go, "Refaire les fichiers déjà traités", how
 * far the list got, and the main button -- "Appliquer le style", or while
 * it runs its progress and "Annuler l'export". */
export function BatchFooter({
  outputDir,
  onOutputDirChange,
  force,
  onForceChange,
  progress,
  running,
  runLabel,
  runShare,
  runnable,
  onRun,
  onCancel,
}: {
  outputDir: string | null;
  onOutputDirChange: (dir: string | null) => void;
  force: boolean;
  onForceChange: (force: boolean) => void;
  progress: ReactNode;
  running: boolean;
  /** While running: "Application · 4/9", and how much of it is done (0 to 1). */
  runLabel: string;
  runShare: number;
  runnable: number;
  onRun: () => void;
  onCancel: () => void;
}) {
  const t = useT();
  return (
    <div className="batch-footer panel">
      <OutputChooser outputDir={outputDir} onOutputDirChange={onOutputDirChange} disabled={running} />
      <label className="check-row">
        <input type="checkbox" checked={force} onChange={(e) => onForceChange(e.target.checked)} disabled={running} />
        {t.output.redo}
      </label>
      <span className="batch-progress">{progress}</span>
      {running ? (
        <>
          <button className="export-cancel" onClick={onCancel}>
            {t.common.cancelExport}
          </button>
          <button className="primary-button run-progress" disabled>
            <span className="run-progress-fill" style={{ width: `${Math.round(runShare * 100)}%` }} aria-hidden="true" />
            <span className="run-progress-label">{runLabel}</span>
          </button>
        </>
      ) : (
        <button className="primary-button" onClick={onRun} disabled={runnable === 0}>
          {t.output.apply(runnable)}
        </button>
      )}
    </div>
  );
}
