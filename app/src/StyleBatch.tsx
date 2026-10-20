import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { cancelJob, expandPaths, planFile, planOutputs, startMux, type MuxResult, type Processing } from "./api";
import {
  BatchFooter,
  isAlreadyDone,
  isRunnable,
  limiter,
  loadOutputDir,
  RevealButton,
  rowState,
  saveOutputDir,
  useRowBadge,
  type FileItem,
} from "./batchShared";
import { FileDetail } from "./Detail";
import { MultiSelect, Select } from "./Dropdown";
import { DropZone } from "./DropZone";
import { DropOverlay, useFileDrop } from "./FileDrop";
import { useT } from "./i18n";
import { FontIcon, ScreenIcon, TagIcon } from "./icons";
import { InfoTip } from "./InfoTip";
import { languageName, USUAL_LANGUAGES } from "./languages";
import { JobCancelled, runJob } from "./jobs";
import { pickFolders, pickMediaFiles } from "./mediaDialog";
import { basename, parentName } from "./paths";
import {
  loadRecursive,
  saveDefaultLanguage,
  saveLanguages,
  saveRecursive,
  useDefaultLanguage,
  useLanguages,
  useListCollapsed,
  useRecursive,
} from "./settings";
import { HOUSE_STYLE, loadStyles, saveListStyle, styleNamed, useListStyle, useStyles } from "./styles";
import { StylesDialog } from "./StylesDialog";
import { devParam, errorMessage } from "./util";
import { EmptyWorkspace, FoldButton, ListRow, MoveButtons, RemoveAllButton, useListKeys } from "./Workspace";
import "./BatchView.css";

// Files read, and remuxed, at the same time: more only makes the disk seek.
const PLANNING = limiter(2);
const MUXING = 2;

/** The workspace (Bobine Audio's MultiTrackBatch, for this app's one way of
 * working): MKVs added one by one or by folder (a season, a series), each
 * read at once -- its subtitle tracks in the chosen languages, what they'll
 * become, the fonts to attach -- then processed: the house style, the
 * tracks named and flagged, the file remuxed into the output folder and
 * checked. */
export function StyleBatch() {
  const t = useT();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [outputDir, setOutputDir] = useState<string | null>(loadOutputDir);
  const [force, setForce] = useState(false);
  const [running, setRunning] = useState(false);
  const [outputsVersion, setOutputsVersion] = useState(0);
  const [addError, setAddError] = useState<string | null>(null);
  const recursive = useRecursive();
  const collapsed = useListCollapsed();
  const rowBadge = useRowBadge();
  // The subtitles' languages to restyle, and the one whose track becomes
  // the default (the first chosen when it isn't among them).
  const languages = useLanguages();
  const defaultChoice = useDefaultLanguage();
  const defaultLanguage = defaultChoice && languages.includes(defaultChoice) ? defaultChoice : (languages[0] ?? null);
  // The styles: the list's, and one picked for a file in its detail.
  const customStyles = useStyles();
  const listStyle = useListStyle();
  const [styleOverrides, setStyleOverrides] = useState<Record<string, string>>({});
  const [stylesOpen, setStylesOpen] = useState(false);
  useEffect(() => {
    loadStyles();
  }, []);

  /** What `path` is processed with now: the languages and its style. */
  const processingOf = useCallback(
    (path: string): Processing => {
      const style = styleNamed(customStyles, styleOverrides[path] ?? listStyle);
      return { languages, default_language: defaultLanguage, style: style.name ? style : null };
    },
    [languages, defaultLanguage, customStyles, styleOverrides, listStyle],
  );
  const processingRef = useRef(processingOf);
  processingRef.current = processingOf;
  // What each file was last read with: read again when that changes.
  const readKeys = useRef(new Map<string, string>());
  const cancelled = useRef(false);
  const filesRef = useRef(files);
  filesRef.current = files;

  const update = useCallback((path: string, patch: Partial<FileItem> | ((f: FileItem) => Partial<FileItem>)) => {
    setFiles((fs) => fs.map((f) => (f.path === path ? { ...f, ...(typeof patch === "function" ? patch(f) : patch) } : f)));
  }, []);

  /** Reads what processing `path` does, with what it's processed with now. */
  const readPlan = useCallback(
    (path: string) => {
      const processing = processingRef.current(path);
      const key = JSON.stringify(processing);
      readKeys.current.set(path, key);
      update(path, { status: "planning", error: undefined });
      PLANNING(() => planFile(path, processing))
        .then((plan) => {
          // Changed again meanwhile: the newer reading wins.
          if (readKeys.current.get(path) !== key) return;
          update(path, { plan, status: plan.tracks.some((track) => track.chosen) ? "ready" : "nothing" });
        })
        .catch((e) => {
          if (readKeys.current.get(path) === key) update(path, { status: "plan_error", error: errorMessage(e) });
        });
    },
    [update],
  );

  /** Adds the MKVs of `paths` not in the list yet (a folder: its MKVs, its
   * seasons' too if "Inclure les sous-dossiers"), each read at once. */
  const add = useCallback(
    async (paths: string[], expanded = false) => {
      setAddError(null);
      let found: string[];
      try {
        found = expanded ? paths : await expandPaths(paths, loadRecursive());
      } catch (e) {
        setAddError(errorMessage(e));
        return;
      }
      const known = new Set(filesRef.current.map((f) => f.path));
      const added = [...new Set(found)].filter((p) => !known.has(p));
      if (found.length === 0) setAddError(t.add.noMkv);
      if (added.length === 0) return;
      // Each read at once (see the effect reading the files).
      setFiles((fs) => [...fs, ...added.map((path) => ({ path, status: "planning" as const }))]);
    },
    [t],
  );

  // Every file read as it's added, and again when what it's processed with
  // changes (languages, its style, that style edited) -- not while
  // processing: the settings wait for it.
  useEffect(() => {
    if (running) return;
    for (const f of files) {
      if (readKeys.current.get(f.path) !== JSON.stringify(processingOf(f.path))) readPlan(f.path);
    }
  }, [files, running, processingOf, readPlan]);

  const dropBlocked = running ? t.add.dropBlocked : null;
  // Dropped paths come expanded already (FileDrop, with the same setting).
  const fileDrag = useFileDrop(true, dropBlocked, (paths) => add(paths, true));

  // A file is always shown while the list has some: the first one listed,
  // or the next one up when the shown one is removed.
  useEffect(() => {
    if (selected !== null && files.some((f) => f.path === selected)) return;
    setSelected(files[0]?.path ?? null);
  }, [files, selected]);

  const selectedIndex = files.findIndex((f) => f.path === selected);
  useListKeys(true, files.length, selectedIndex, (i) => setSelected(files[i].path));

  // Dev only (see devParam): `?files=a|b` adds files, and automated checks
  // add them with window.__test.add(paths).
  useEffect(() => {
    const list = devParam("files");
    if (list) add(list.split("|"));
    if (import.meta.env.DEV) (window as unknown as { __test: object }).__test = { add };
  }, [add]);

  // Where each file goes, and whether it's already there.
  const pathsKey = files.map((f) => f.path).join("\n");
  useEffect(() => {
    const sources = pathsKey ? pathsKey.split("\n") : [];
    if (sources.length === 0) return;
    let stale = false;
    planOutputs(sources, outputDir)
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
  }, [pathsKey, outputDir, outputsVersion]);

  const runnable = files.filter((f) => isRunnable(f, force));
  const finished = files.filter((f) => f.status === "done").length;
  const busy = files.filter((f) => f.status === "queued" || f.status === "running");
  const failed = files.filter((f) => f.status === "error").length;
  const alreadyDone = files.filter((f) => isAlreadyDone(f, force)).length;
  const nothing = files.filter((f) => f.status === "nothing").length;

  /** Processes `targets` (the main button: every runnable file; the
   * detail's button: that one, written again if it was). */
  async function run(targets: FileItem[]) {
    const batch = targets.map((f) => ({ path: f.path, output: f.output!.path }));
    if (batch.length === 0) return;
    cancelled.current = false;
    setRunning(true);
    setFiles((fs) =>
      fs.map((f) => (batch.some((b) => b.path === f.path) ? { ...f, status: "queued", progress: 0, error: undefined, log: [] } : f)),
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
              startMux(path, output, processingRef.current(path)),
              (message) => update(path, (f) => ({ log: [...(f.log ?? []), message] })),
              (jobId) => update(path, { jobId }),
              (progress) => update(path, { progress }),
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

  function changeOutputDir(dir: string | null) {
    setOutputDir(dir);
    saveOutputDir(dir);
  }

  async function pickFiles() {
    const picked = await pickMediaFiles();
    if (picked) add(picked);
  }

  async function pickFolder() {
    const picked = await pickFolders();
    if (picked) add(picked);
  }

  const current = files.find((f) => f.path === selected) ?? null;
  // Seasons apart: a header over each folder's files when they come from
  // several.
  const grouped = new Set(files.map((f) => parentName(f.path))).size > 1;
  const runTotal = finished + busy.length;
  // Every language the files' subtitles are in, the chosen ones first;
  // the usual ones while none is read yet.
  const found = files.flatMap((f) => f.plan?.tracks.map((track) => track.language) ?? []);
  const languageOptions = [...new Set([...languages, ...(found.length > 0 ? found : USUAL_LANGUAGES)])]
    .filter((code): code is string => !!code)
    .map((code) => ({ value: code, label: languageName(code) }));

  return (
    <main className="batch-main">
      {files.length === 0 ? (
        <EmptyWorkspace title={t.empty.title} hint={t.empty.hint}>
          <DropZone title={t.empty.drop} disabled={running} onClick={pickFiles}>
            {t.empty.dropHint}
          </DropZone>
          <div className="empty-add">
            <button onClick={pickFolder}>{t.add.folder}</button>
            <label className="check-row">
              <input type="checkbox" checked={recursive} onChange={(e) => saveRecursive(e.target.checked)} />
              {t.add.recursive}
            </label>
          </div>
          {addError && <p className="error">{addError}</p>}
          <div className="mode-cards">
            {(
              [
                [<FontIcon />, t.empty.styleTitle, t.empty.styleHint],
                [<ScreenIcon />, t.empty.sizeTitle, t.empty.sizeHint],
                [<TagIcon />, t.empty.tracksTitle, t.empty.tracksHint],
              ] as const
            ).map(([icon, title, hint]) => (
              <div key={title} className="mode-card">
                <span className="mode-card-title">
                  {icon}
                  <span>{title}</span>
                </span>
                <span className="mode-card-hint">{hint}</span>
              </div>
            ))}
          </div>
        </EmptyWorkspace>
      ) : (
        <>
          <div className="batch-config panel">
            <span className="config-field">
              {t.languages.label}
              <MultiSelect
                label={t.languages.label}
                values={languages}
                options={languageOptions}
                onChange={saveLanguages}
                placeholder={t.languages.none}
                disabled={running}
              />
            </span>
            <span className="config-field">
              {t.languages.defaultLabel}
              <Select
                label={t.languages.defaultLabel}
                value={defaultLanguage ?? ""}
                options={languages.map((code) => ({ value: code, label: languageName(code) }))}
                onChange={saveDefaultLanguage}
                disabled={running}
              />
            </span>
            <span className="config-field">
              {t.styles.label}
              <Select
                label={t.styles.label}
                value={styleNamed(customStyles, listStyle).name}
                options={[HOUSE_STYLE, ...customStyles].map((s) => ({ value: s.name, label: s.name || t.styles.house }))}
                onChange={saveListStyle}
                disabled={running}
              />
            </span>
            <button className="small-button" onClick={() => setStylesOpen(true)}>
              {t.styles.edit}
            </button>
            <InfoTip>{t.languages.hint}</InfoTip>
          </div>

          <div className={`workspace${collapsed ? " list-collapsed" : ""}`}>
            <section className="panel file-list">
              <div className="file-list-header">
                <h2>{t.list.count(files.length)}</h2>
                <RemoveAllButton
                  results={false}
                  disabled={running}
                  onRemove={() => {
                    setFiles([]);
                    setAddError(null);
                    setStyleOverrides({});
                    readKeys.current.clear();
                  }}
                />
                <FoldButton collapsed={collapsed} />
              </div>

              <ul className="file-list-rows list-scroll">
                {files.map((f, i) => {
                  const [badge, badgeKind] = rowBadge(f, force);
                  const group = parentName(f.path);
                  const header = grouped && (i === 0 || parentName(files[i - 1].path) !== group);
                  return (
                    <ListRowGroup key={f.path} header={header ? group : null}>
                      <ListRow
                        name={basename(f.path)}
                        path={f.path}
                        selected={f.path === selected}
                        onSelect={() => setSelected(f.path)}
                        state={rowState(f, force)}
                        badge={badge}
                        badgeKind={badgeKind}
                        progress={f.status === "running" ? (f.progress ?? 0) : undefined}
                        detail={<RowDetail file={f} />}
                        actions={
                          <>
                            {f.status !== "running" && <RevealButton file={f.output?.exists ? f.output.path : undefined} />}
                            <MoveButtons count={files.length} index={i} disabled={running} onChange={(move) => setFiles(move)} />
                          </>
                        }
                      />
                    </ListRowGroup>
                  );
                })}
              </ul>
              {addError && <p className="error file-list-error">{addError}</p>}
              {/* Adding more: a click picks files, or they're dropped on the window. */}
              <button className="file-list-add" disabled={running} title={t.add.addHint} onClick={pickFiles}>
                <span>{t.add.addMore}</span>
                <span>{t.add.dropMore}</span>
              </button>
            </section>

            {current && (
              <FileDetail
                file={current}
                running={running}
                primary={files.length === 1}
                onRun={() => run([current])}
                styles={customStyles}
                listStyle={listStyle}
                styleOverride={styleOverrides[current.path] ?? null}
                onStyleChange={(name) =>
                  setStyleOverrides((o) => {
                    const next = { ...o };
                    if (name === null) delete next[current.path];
                    else next[current.path] = name;
                    return next;
                  })
                }
              />
            )}
          </div>

          <BatchFooter
            outputDir={outputDir}
            onOutputDirChange={changeOutputDir}
            force={force}
            onForceChange={setForce}
            progress={t.output.summary({
              files: files.length,
              toDo: runnable.length,
              done: finished,
              already: alreadyDone,
              nothing,
              failed,
            })}
            running={running}
            runLabel={t.output.running(finished, runTotal)}
            runShare={runTotal > 0 ? (finished + busy.reduce((n, f) => n + (f.progress ?? 0), 0)) / runTotal : 0}
            runnable={runnable.length}
            onRun={() => run(runnable)}
            onCancel={cancel}
          />
        </>
      )}
      {stylesOpen && <StylesDialog onClose={() => setStylesOpen(false)} />}
      <DropOverlay drag={fileDrag} blocked={dropBlocked} label={t.add.dropToAdd} hint={recursive ? t.add.dropRecursive : undefined} />
    </main>
  );
}

/** A row, under its folder's name when it starts a new one (a season). */
function ListRowGroup({ header, children }: { header: string | null; children: ReactNode }) {
  return (
    <>
      {header && (
        <li className="list-group" aria-hidden="true">
          {header}
        </li>
      )}
      {children}
    </>
  );
}

/** Under a row's name: its tracks in the chosen languages ("fre complets +
 * forcés · eng complets (SRT)"), or why there's nothing to do. */
function RowDetail({ file }: { file: FileItem }) {
  const t = useT();
  if (file.status === "planning") return <>{t.detail.readingTracks}</>;
  if (file.status === "plan_error") return <span className="error">{file.error}</span>;
  if (!file.plan) return null;
  const chosen = file.plan.tracks.filter((track) => track.chosen);
  if (chosen.length === 0) return <>{t.list.noChosen}</>;
  const byLanguage = [...new Set(chosen.map((track) => track.language))].map(
    (language) =>
      `${language ?? "?"} ` +
      chosen
        .filter((track) => track.language === language)
        .map((track) => (track.kind === "forced" ? t.list.forced : t.list.full) + (track.action === "convert" ? " (SRT)" : ""))
        .join(" + "),
  );
  return (
    <>
      {byLanguage.join(" · ")}
      {file.plan.fonts.length > 0 && ` · ${t.list.fonts(file.plan.fonts.length)}`}
    </>
  );
}
