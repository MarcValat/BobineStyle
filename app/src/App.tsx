import { useCallback, useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { cancelJob, expandPaths, JobCancelled, type MuxResult, planFile, planOutputs, runJob, startMux } from "./api";
import { EngineStatusBadge } from "./EngineStatus";
import { DropOverlay, useFileDrop } from "./FileDrop";
import FileTable from "./FileTable";
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
      if (found.length === 0) setAddError("Aucun fichier MKV là-dedans.");
      if (added.length === 0) return;
      setFiles((fs) => [...fs, ...added.map((path) => ({ path, status: "planning" as const }))]);
      setSelected((s) => s ?? added[0]);
      for (const path of added) {
        PLANNING(() => planFile(path))
          .then((plan) => update(path, { plan, status: plan.tracks.some((t) => t.french) ? "ready" : "no_french" }))
          .catch((e) => update(path, { status: "plan_error", error: errorMessage(e) }));
      }
    },
    [recursive, update],
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
    setFiles((fs) =>
      fs.map((f) => (batch.some((b) => b.path === f.path) ? { ...f, status: "queued", progress: 0, error: undefined } : f)),
    );
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
    const picked = await open({ title: "Ajouter des MKV", multiple: true, filters: [{ name: "Vidéos MKV", extensions: ["mkv"] }] });
    if (picked) add(Array.isArray(picked) ? picked : [picked]);
  }

  async function pickFolders() {
    const picked = await open({ title: "Ajouter un dossier", directory: true, multiple: true });
    if (picked) add(Array.isArray(picked) ? picked : [picked]);
  }

  async function pickOutputFolder() {
    const picked = await open({ title: "Dossier de sortie", directory: true, multiple: false });
    if (typeof picked === "string") setFolder(picked);
  }

  const dragging = useFileDrop(true, running ? "Traitement en cours" : null, add);

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
            <h2>Ajouter</h2>
            <button className="primary-button file-open-button" onClick={pickFiles} disabled={running}>
              Ajouter des MKV…
            </button>
            <button className="file-open-button" onClick={pickFolders} disabled={running}>
              Ajouter un dossier…
            </button>
            <label className="check-row">
              <input type="checkbox" checked={recursive} onChange={(e) => setRecursive(e.target.checked)} />
              Inclure les sous-dossiers (saisons)
            </label>
            {addError && <p className="error">{addError}</p>}
          </section>

          <section className="panel run-panel">
            <h2>Sortie</h2>
            <PillSwitch
              className="pill-switch-wide"
              label="Où écrire les fichiers traités"
              options={[
                ["next", "À côté des originaux"],
                ["folder", "Autre dossier"],
              ]}
              value={folder === null ? "next" : "folder"}
              onChange={(choice) => (choice === "next" ? setFolder(null) : pickOutputFolder())}
              disabled={running}
            />
            {folder === null ? (
              <p className="output-current">
                Dans un dossier « Output », sous le même nom
                <InfoTip>Chaque fichier traité garde son nom, dans un dossier « Output » à côté de l'original. Les originaux ne sont jamais modifiés.</InfoTip>
              </p>
            ) : (
              <div className="output-folder">
                <div className="file-path" title={folder}>
                  {folder}
                </div>
                <button className="small-button" onClick={pickOutputFolder} disabled={running}>
                  Changer…
                </button>
              </div>
            )}
            <label className="check-row">
              <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} disabled={running} />
              Refaire les fichiers déjà traités
            </label>
            <div className="export-box">
              <p className="export-summary">
                {files.length} fichier{files.length > 1 ? "s" : ""} · {runnable.length} à traiter
                {finished > 0 && ` · ${finished} traité${finished > 1 ? "s" : ""}`}
              </p>
              {running ? (
                <div className="export-running">
                  <span className="export-running-label">
                    Traitement… {finished} / {finished + queued}
                  </span>
                  <button className="export-cancel" onClick={cancel}>
                    Annuler l'export
                  </button>
                </div>
              ) : (
                <button className="primary-button export-button" onClick={() => run(runnable)} disabled={runnable.length === 0}>
                  Appliquer le style{runnable.length > 0 ? ` (${runnable.length})` : ""}
                </button>
              )}
            </div>
          </section>
        </div>

        <div className="right-column">
          <section className="panel files-panel">
            <div className="panel-header">
              <h2>Fichiers</h2>
              <button
                className="small-button"
                disabled={running || files.length === 0}
                onClick={() => {
                  setFiles([]);
                  setSelected(null);
                }}
              >
                Tout retirer
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
        blocked={running ? "Attends la fin du traitement" : null}
        label="Ajouter à la liste"
        hint={recursive ? "Les dossiers sont parcourus avec leurs sous-dossiers" : undefined}
      />
    </div>
  );
}
