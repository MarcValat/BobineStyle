import { useCallback, useEffect, useRef, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { cancelJob, expandPaths, JobCancelled, type MuxResult, planFile, planOutputs, runJob, startMux } from "./api";
import { retryEngine, useEngineStatus } from "./engine";
import { DropOverlay, useFileDrop } from "./FileDrop";
import FileTable from "./FileTable";
import PlanDetail from "./PlanDetail";
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

  async function run() {
    const batch = runnable.map((f) => ({ path: f.path, output: f.output!.path }));
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

  return (
    <div className="app">
      <div className="layout">
        <aside className="sidebar">
          <EngineBadge />
          <section className="card">
            <h2>Fichiers</h2>
            <p className="hint">Des MKV, ou un dossier entier (une saison, une série). Tu peux aussi les glisser dans la fenêtre.</p>
            <button className="primary wide" onClick={pickFiles} disabled={running}>
              Ajouter des MKV…
            </button>
            <button className="wide" onClick={pickFolders} disabled={running}>
              Ajouter un dossier…
            </button>
            <label className="checkbox">
              <input type="checkbox" checked={recursive} onChange={(e) => setRecursive(e.target.checked)} />
              Inclure les sous-dossiers (saisons)
            </label>
            {addError && <p className="error">{addError}</p>}
            {files.length > 0 && (
              <div className="list-info">
                <span className="muted">
                  {files.length} fichier{files.length > 1 ? "s" : ""}
                </span>
                {!running && (
                  <button
                    className="link"
                    onClick={() => {
                      setFiles([]);
                      setSelected(null);
                    }}
                  >
                    Vider la liste
                  </button>
                )}
              </div>
            )}
          </section>

          <section className="card">
            <h2>Sortie</h2>
            <div className="segmented">
              <button className={folder === null ? "active" : ""} onClick={() => setFolder(null)} disabled={running}>
                Output à côté
              </button>
              <button className={folder !== null ? "active" : ""} onClick={pickOutputFolder} disabled={running}>
                Autre dossier
              </button>
            </div>
            {folder === null ? (
              <p className="hint">Dans un dossier « Output » à côté de chaque fichier, sous le même nom. Les originaux ne sont jamais modifiés.</p>
            ) : (
              <div className="file-name" title={folder}>
                {folder}
              </div>
            )}
            <label className="checkbox">
              <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} disabled={running} />
              Refaire les fichiers déjà traités
            </label>
          </section>

          <button className="primary wide big" onClick={run} disabled={running || runnable.length === 0}>
            {running
              ? `Traitement… (${finished} / ${finished + files.filter((f) => f.status === "queued" || f.status === "running").length})`
              : `Appliquer le style${runnable.length > 0 ? ` (${runnable.length})` : ""}`}
          </button>
          {running && (
            <button className="wide" onClick={cancel}>
              Annuler
            </button>
          )}
        </aside>

        <main className="results">
          {files.length === 0 ? (
            <EmptyState />
          ) : (
            <div className="results-content">
              <section className="card">
                <FileTable
                  files={files}
                  selected={current?.path ?? null}
                  running={running}
                  force={force}
                  onSelect={setSelected}
                  onRemove={remove}
                />
              </section>
              {current && <PlanDetail file={current} />}
            </div>
          )}
        </main>
      </div>
      <DropOverlay
        dragging={dragging}
        blocked={running ? "Attends la fin du traitement" : null}
        label="Ajouter à la liste"
        hint={recursive ? "Les dossiers sont parcourus avec leurs sous-dossiers" : undefined}
      />
    </div>
  );
}

function EngineBadge() {
  const status = useEngineStatus();
  if (status === "ready") return null;
  return (
    <span className={`engine-badge ${status}`}>
      {status === "starting" ? (
        "Démarrage du moteur…"
      ) : (
        <>
          Moteur injoignable <button onClick={retryEngine}>Réessayer</button>
        </>
      )}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="placeholder">
      <div className="placeholder-title">Ajoute des MKV pour commencer.</div>
      <p>
        Bobine Style applique le style maison (Trebuchet MS, contour et ombre) aux sous-titres français, adapté à la résolution de chaque
        vidéo. Il nomme les pistes complètes et forcées, joint les polices, et laisse le reste du fichier intact.
      </p>
      <p className="muted">Les fichiers traités vont dans un dossier Output : les originaux ne sont jamais modifiés.</p>
    </div>
  );
}
