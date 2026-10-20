import { revealItemInDir } from "@tauri-apps/plugin-opener";
import type { PlannedTrack } from "./api";
import { isRedoable, type FileItem } from "./batchShared";
import { useT } from "./i18n";
import { FolderIcon, RedoIcon } from "./icons";
import { Tooltip } from "./InfoTip";
import { LogPanel } from "./LogPanel";
import { languageName } from "./languages";
import { basename } from "./paths";

/** The selected file's detail (Workspace.css, after Bobine Audio's
 * Detail.tsx): its header with its buttons, what processing it does --
 * the default track and why, each subtitle track's fate, the style, the
 * fonts -- and how its run went. */
export function FileDetail({
  file,
  running,
  primary,
  onRun,
}: {
  file: FileItem;
  /** Something runs: nothing starts. */
  running: boolean;
  /** It's alone in the list: its button is the window's main one. */
  primary: boolean;
  onRun: () => void;
}) {
  const t = useT();
  const plan = file.plan;
  const chosen = plan?.tracks.filter((track) => track.chosen) ?? [];
  const defaultName = plan?.default_language ? t.languages.inSentence(languageName(plan.default_language)) : null;
  const hasDefault = chosen.some((track) => track.language === plan?.default_language);
  const written = file.output?.exists ? file.output.path : undefined;
  const redo = isRedoable(file) && !!file.output?.exists;
  return (
    <section className="panel file-detail">
      <div className="detail-header">
        <div className="detail-title">
          <span className="detail-name" title={file.path}>
            {basename(file.path)}
          </span>
          <span className="detail-meta">{plan ? <DetailMeta file={file} /> : file.status === "planning" && t.detail.readingTracks}</span>
        </div>
        {redo && (
          <Tooltip text={t.list.redo}>
            <button className="icon-small-button detail-icon-button" disabled={running} onClick={onRun} aria-label={t.list.redo}>
              <RedoIcon />
            </button>
          </Tooltip>
        )}
        {written && file.status !== "running" && (
          <button onClick={() => revealItemInDir(written)}>
            <FolderIcon />
            {t.detail.openFolder}
          </button>
        )}
        {isRedoable(file) && !file.output?.exists && (
          <button className={primary ? "primary-button" : ""} disabled={running} onClick={onRun}>
            {t.detail.applyFile}
          </button>
        )}
      </div>

      <div className="detail-body list-scroll">
        <RunStatus file={file} />
        {file.status === "plan_error" && file.error && <p className="error">{file.error}</p>}
        {plan && chosen.length === 0 && (
          <p className="placeholder">{plan.tracks.length === 0 ? t.detail.noSubtitles : t.detail.noChosen}</p>
        )}
        {plan && chosen.length > 0 && (
          <>
            <p className="detail-default">
              {!hasDefault || !defaultName ? (
                t.detail.noDefaultTrack(defaultName ?? "?")
              ) : plan.audio ? (
                <>
                  {t.detail.defaultAudio}
                  <strong>{t.languages.inSentence(languageName(plan.audio.language))}</strong>
                  {plan.audio.title && <span className="muted"> ({plan.audio.title})</span>}
                  {t.detail.defaultSubtitles}
                  <strong>{t.detail.defaultKind(plan.audio.same, defaultName)}</strong>
                  {t.detail.byDefault}
                </>
              ) : (
                t.detail.noAudio(defaultName)
              )}
            </p>

            <div className="detail-style">
              <span className="detail-style-label">{t.detail.style}</span>
              <span className="detail-style-name">{t.detail.houseStyle}</span>
              <span className="detail-style-summary">{t.detail.houseStyleSummary}</span>
              {plan.video_size && <span className="detail-style-scale">{t.detail.scaled(plan.video_size[0], plan.video_size[1])}</span>}
            </div>

            <div className="tracks-table-wrap">
              <table className="detail-tracks-table">
                <thead>
                  <tr>
                    <th>{t.detail.track}</th>
                    <th>{t.detail.becomes}</th>
                    <th>{t.detail.flags}</th>
                    <th>{t.detail.processing}</th>
                  </tr>
                </thead>
                {plan.tracks.map((track) => (
                  <TrackRows key={track.index} track={track} />
                ))}
              </table>
            </div>

            <dl className="detail-facts">
              {plan.fonts.length > 0 && (
                <>
                  <dt>{t.detail.attachedFonts}</dt>
                  <dd>{plan.fonts.join(", ")}</dd>
                </>
              )}
              {plan.fonts_present.length > 0 && (
                <>
                  <dt>{t.detail.presentFonts}</dt>
                  <dd>{plan.fonts_present.join(", ")}</dd>
                </>
              )}
              {file.output && (
                <>
                  <dt>{file.output.exists ? t.detail.written : t.detail.output}</dt>
                  <dd className="detail-path" title={file.output.path}>
                    {file.output.path}
                  </dd>
                </>
              )}
            </dl>
            {plan.warnings.map((w) => (
              <p key={w} className="warning">
                {w}
              </p>
            ))}
          </>
        )}
      </div>
    </section>
  );
}

/** "1920×1080 · sous-titres : 2 français · 1 anglais". */
function DetailMeta({ file }: { file: FileItem }) {
  const t = useT();
  const plan = file.plan!;
  const counts = new Map<string, number>();
  for (const track of plan.tracks) {
    const name = t.languages.inSentence(languageName(track.language));
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  const subs = [...counts].map(([name, n]) => `${n} ${name}`).join(" · ");
  const size = plan.video_size ? `${plan.video_size[0]}×${plan.video_size[1]}` : null;
  return <>{[size, subs ? t.detail.subtitles(subs) : t.detail.noSubtitlesShort].filter(Boolean).join(" · ")}</>;
}

/** How the file's last run went: running, written, failed, cancelled --
 * with its log. Nothing before a run. */
function RunStatus({ file }: { file: FileItem }) {
  const t = useT();
  const log = file.log ?? [];
  if (file.status === "running") {
    return (
      <p className="detail-run batch-status-running">
        <span className="spinner spinner-small" aria-hidden="true" />
        {t.detail.running(Math.round((file.progress ?? 0) * 100))}
        <LogPanel lines={log} />
      </p>
    );
  }
  if (file.status === "done") {
    return (
      <p className="detail-run batch-status-done">
        <span className="render-success">{t.detail.doneRun}</span>
        <LogPanel lines={log} />
      </p>
    );
  }
  if (file.status === "error") {
    return (
      <div className="detail-run detail-run-error" role="alert">
        <span>{t.detail.failedRun(file.error ?? t.common.error)}</span>
        <LogPanel lines={log} />
      </div>
    );
  }
  if (file.status === "cancelled") return <p className="detail-run batch-status-cancelled">{t.detail.cancelledRun}</p>;
  return null;
}

/** A track and its notes: one group, tinted as one in the table. */
function TrackRows({ track }: { track: PlannedTrack }) {
  const t = useT();
  const current = [languageName(track.language), track.codec, track.title && t.detail.titled(track.title)].filter(Boolean).join(" · ");
  return (
    <tbody>
      <tr className={track.chosen ? "" : "dim"}>
        <td>
          <span className="muted">#{track.index}</span> {current}
        </td>
        <td>{track.chosen ? track.new_title : <span className="muted">{t.detail.unchanged}</span>}</td>
        <td>
          {track.default && <span className="pill pill-accent">{t.detail.flagDefault}</span>}
          {track.forced && <span className="pill">{t.detail.flagForced}</span>}
        </td>
        <td>
          {t.detail.actions[track.action]}
          {!track.chosen && <span className="muted"> · {t.detail.notChosen}</span>}
          {track.dialogue_lines !== null && <span className="muted"> · {t.detail.lines(track.dialogue_lines)}</span>}
        </td>
      </tr>
      {track.notes.length > 0 && (
        <tr className="notes">
          <td colSpan={4}>
            {track.notes.map((n) => (
              <span key={n} className="note">
                {n}
              </span>
            ))}
          </td>
        </tr>
      )}
    </tbody>
  );
}
