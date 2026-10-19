import { useCallback, useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { cancelJob, expandPaths, JobCancelled, type MuxResult, planFile, planOutputs, runJob, setEngineLanguage, startMux } from "./api";
import { EngineStatusBadge } from "./EngineStatus";
import { DropOverlay, useFileDrop } from "./FileDrop";
import FileTable from "./FileTable";
import { useLanguage, useT } from "./i18n";
import { InfoTip } from "./InfoTip";
import { OptionsButton } from "./Options";
import PlanDetail from "./PlanDetail";
import { PillSwitch } from "./PillSwitch";
import { UpdateButton } from "./UpdateButton";
import { errorMessage, type FileItem, isRunnable, limiter } from "./shared";

// Files read, and remuxed, at the same time: more only makes the disk seek.
const PLANNING = limiter(2);
const MUXING = 2;

export default function App() {
  const t = useT();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [recursive, setRecursive] = useState(true);
  const [folder, setFolder] = useState<string | null>(null); // null: Output/ next to each file
  const [force, setForce] = useState(false);
  const [running, setRunning] = useState(false);
  const [outputsVersion, setOutputsVersion] = useState(0);
  const [addError, setAddError] = useState<string | null>(null);
  const cancelled = useRef(false);
  const filesRef = useRef(files);
  filesRef.current = files;

  // The engine's messages (plan notes, job logs, errors) in the UI's
  // language whenever it changes (engine.ts sends it once the engine is up).
  const language = useLanguage();
  useEffect(() => {
    setEngineLanguage(language).catch(() => {});
  }, [language]);

  const update = useCallback((path: string, patch: Partial<FileItem>) => {
    setFiles((fs) => fs.map((f) => (f.path === path ? { ...f, ...patch } : f)));
  }, []);

  const add = useCallback(
    async (paths: string[]) => {
      setAddError(null);
      let found: string[];
      try {
        found = await expandPaths(paths, recursive);
      } catch (e) {
        setAddError(errorMessage(e));
        return;
      }
      const known = new Set(filesRef.current.map((f) => f.path));
      const added = found.filter((p) => !known.has(p));
      if (found.length === 0) setAddError(t.add.noMkv);
      if (added.length === 0) return;
      setFiles((fs) => [...fs, ...added.map((path) => ({ path, status: "planning" as const }))]);
      setSelected((s) => s ?? added[0]);
      for (const path of added) {
        PLANNING(() => planFile(path))
          .then((plan) => update(path, { plan, status: plan.tracks.some((t) => t.french) ? "ready" : "no_french" }))
          .catch((e) => update(path, { status: "plan_error", error: errorMessage(e) }));
      }
    },
    [recursive, update, t],
  );

  // Where each file goes, and whether it's already there.
  const pathsKey = files.map((f) => f.path).join("\n");
  useEffect(() => {
    const sources = pathsKey ? pathsKey.split("\n") : [];
    if (sources.length === 0) return;
    let stale = false;
    planOutputs(sources, folder)
      .then((outputs) => {
        if (stale) return;
        const bySource = new Map(sources.map((s, i) => [s, outputs[i]]));
        setFiles((fs) => fs.map((f) => ({ ...f, output: bySource.get(f.path) ?? f.output })));
      })
      .catch(() => {
        // the engine is down: the badge says so
      });
    return () => {
      stale = true;
    };
  }, [pathsKey, folder, outputsVersion]);

  const runnable = files.filter((f) => isRunnable(f, force));
  const finished = files.filter((f) => f.status === "done").length;

  /** Processes `targets` (the main button: every runnable file; a row's
   * "Refaire ce fichier": that one, written again). */
  async function run(targets: FileItem[]) {
    const batch = targets.map((f) => ({ path: f.path, output: f.output!.path }));
    if (batch.length === 0) return;
    cancelled.current = false;
    setRunning(true);
    setFiles((fs) => fs.map((f) => (batch.some((b) => b.path === f.path) ? { ...f, status: "queued", progress: 0, error: undefined } : f)));
    const muxing = limiter(MUXING);
    await Promise.all(
      batch.map(({ path, output }) =>
        muxing(async () => {
          if (cancelled.current) {
            update(path, { status: "ready" });
            return;
          }
          update(path, { status: "running" });
          try {
            const result = await runJob<MuxResult>(
              startMux(path, output),
              (progress) => update(path, { progress }),
              (jobId) => update(path, { jobId }),
            );
            update(path, { status: "done", plan: result.plan, progress: 1 });
          } catch (e) {
            if (e instanceof JobCancelled) update(path, { status: "cancelled" });
            else update(path, { status: "error", error: errorMessage(e) });
          }
        }),
      ),
    );
    setRunning(false);
    setOutputsVersion((v) => v + 1);
  }

  function cancel() {
    cancelled.current = true;
    for (const f of filesRef.current) if (f.status === "running" && f.jobId) cancelJob(f.jobId).catch(() => {});
  }

  function remove(path: string) {
    setFiles((fs) => fs.filter((f) => f.path !== path));
    if (selected === path) setSelected(null);
  }

  async function pickFiles() {
    const picked = await open({ title: t.add.files, multiple: true, filters: [{ name: t.add.mkvFilter, extensions: ["mkv"] }] });
    if (picked) add(Array.isArray(picked) ? picked : [picked]);
  }

  async function pickFolders() {
    const picked = await open({ title: t.add.folderDialog, directory: true, multiple: true });
    if (picked) add(Array.isArray(picked) ? picked : [picked]);
  }

  async function pickOutputFolder() {
    const picked = await open({ title: t.output.folderDialog, directory: true, multiple: false });
    if (typeof picked === "string") setFolder(picked);
  }

  const dragging = useFileDrop(true, running ? t.add.dropBlocked : null, add);

  // Dev only: lets automated checks add files without the native dialog.
  useEffect(() => {
    if (import.meta.env.DEV) (window as unknown as { __test: object }).__test = { add };
  }, [add]);

  const current = files.find((f) => f.path === selected) ?? files[0];
  const queued = files.filter((f) => f.status === "queued" || f.status === "running").length;

  return (
    <div className="container">
      <div className="top-bar">
        <div className="top-actions">
          <EngineStatusBadge />
          <UpdateButton />
          <OptionsButton />
        </div>
      </div>
      <main className="app-main">
        <div className="left-column">
          <section className="panel">
            <h2>{t.add.title}</h2>
            <button className="primary-button file-open-button" onClick={pickFiles} disabled={running}>
              {t.add.files}
            </button>
            <button className="file-open-button" onClick={pickFolders} disabled={running}>
              {t.add.folder}
            </button>
            <label className="check-row">
              <input type="checkbox" checked={recursive} onChange={(e) => setRecursive(e.target.checked)} />
              {t.add.recursive}
            </label>
            {addError && <p className="error">{addError}</p>}
          </section>

          <section className="panel run-panel">
            <h2>{t.output.title}</h2>
            <PillSwitch
              className="pill-switch-wide"
              label={t.output.where}
              options={[
                ["next", t.output.nextTo],
                ["folder", t.output.otherFolder],
              ]}
              value={folder === null ? "next" : "folder"}
              onChange={(choice) => (choice === "next" ? setFolder(null) : pickOutputFolder())}
              disabled={running}
            />
            {folder === null ? (
              <p className="output-current">
                {t.output.nextToText}
                <InfoTip>{t.output.nextToHint}</InfoTip>
              </p>
            ) : (
              <div className="output-folder">
                <div className="file-path" title={folder}>
                  {folder}
                </div>
                <button className="small-button" onClick={pickOutputFolder} disabled={running}>
                  {t.common.change}
                </button>
              </div>
            )}
            <label className="check-row">
              <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} disabled={running} />
              {t.output.redo}
            </label>
            <div className="export-box">
              <p className="export-summary">{t.output.summary(files.length, runnable.length, finished)}</p>
              {running ? (
                <div className="export-running">
                  <span className="export-running-label">{t.output.running(finished, finished + queued)}</span>
                  <button className="export-cancel" onClick={cancel}>
                    {t.common.cancelExport}
                  </button>
                </div>
              ) : (
                <button className="primary-button export-button" onClick={() => run(runnable)} disabled={runnable.length === 0}>
                  {t.output.apply(runnable.length)}
                </button>
              )}
            </div>
          </section>
        </div>

        <div className="right-column">
          <section className="panel files-panel">
            <div className="panel-header">
              <h2>
                {t.list.title} <InfoTip>{t.list.hint}</InfoTip>
              </h2>
              <button
                className="small-button"
                disabled={running || files.length === 0}
                onClick={() => {
                  setFiles([]);
                  setSelected(null);
                }}
              >
                {t.common.removeAll}
              </button>
            </div>
            <div className="file-table-wrap list-scroll">
              <FileTable
                files={files}
                selected={current?.path ?? null}
                running={running}
                force={force}
                onSelect={setSelected}
                onRemove={remove}
                onAdd={pickFiles}
                onRedo={(path) => {
                  const file = files.find((f) => f.path === path);
                  if (file) run([file]);
                }}
              />
            </div>
          </section>
          {current && <PlanDetail file={current} />}
        </div>
      </main>
      <DropOverlay
        dragging={dragging}
        blocked={running ? t.add.dropBlocked : null}
        label={t.add.dropToAdd}
        hint={recursive ? t.add.dropRecursive : undefined}
      />
    </div>
  );
}
