import { revealItemInDir } from "@tauri-apps/plugin-opener";
import type { PlannedTrack } from "./api";
import { useT } from "./i18n";
import { fileName, languageName, type FileItem } from "./shared";

/** Everything processing one file does: each subtitle track's fate, the
 * default track and why, the fonts. */
export default function PlanDetail({ file }: { file: FileItem }) {
  const t = useT();
  const plan = file.plan;
  return (
    <section className="panel detail-panel">
      <div className="panel-header">
        <h2>{t.detail.title}</h2>
        {plan?.video_size && (
          <span className="detail-size">
            {plan.video_size[0]}×{plan.video_size[1]}
          </span>
        )}
      </div>
      <div className="detail-body list-scroll">
        <div className="file-path" title={file.path}>
          {fileName(file.path)}
        </div>
        {file.status === "planning" && <p className="muted">{t.detail.readingTracks}</p>}
        {file.error && <p className="error">{file.error}</p>}
        {plan && !plan.tracks.some((track) => track.french) && (
          <p className="muted">{plan.tracks.length === 0 ? t.detail.noSubtitles : t.detail.noFrench}</p>
        )}
        {plan && plan.tracks.some((track) => track.french) && (
          <>
            <p>
              {plan.audio ? (
                <>
                  {t.detail.defaultAudio}
                  <strong>{t.languages.inSentence(languageName(plan.audio.language))}</strong>
                  {plan.audio.title && <span className="muted"> ({plan.audio.title})</span>}
                  {t.detail.defaultSubtitles}
                  <strong>{plan.audio.french ? t.detail.forced : t.detail.full}</strong>
                  {t.detail.byDefault}
                </>
              ) : (
                <>{t.detail.noAudio}</>
              )}
            </p>
            <div className="tracks-table-wrap">
              <table>
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
            <Fonts attached={plan.fonts} present={plan.fonts_present} />
            {plan.warnings.map((w) => (
              <p key={w} className="warning">
                {w}
              </p>
            ))}
          </>
        )}
        {file.output && file.status !== "no_french" && (
          <div className="output-line">
            <span className="muted">{t.detail.output}</span>
            <span className="file-path" title={file.output.path}>
              {file.output.path}
            </span>
            {file.output.exists && (
              <button className="link" onClick={() => revealItemInDir(file.output!.path)}>
                {t.common.show}
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

/** A track and its notes: one group, tinted as one in the table. */
function TrackRows({ track }: { track: PlannedTrack }) {
  const t = useT();
  const current = [languageName(track.language), track.codec, track.title && t.detail.titled(track.title)].filter(Boolean).join(" · ");
  return (
    <tbody>
      <tr className={track.french ? "" : "dim"}>
        <td>
          <span className="muted">#{track.index}</span> {current}
        </td>
        <td>{track.french ? track.new_title : <span className="muted">{t.detail.unchanged}</span>}</td>
        <td>
          {track.default && <span className="pill pill-accent">{t.detail.flagDefault}</span>}
          {track.forced && <span className="pill">{t.detail.flagForced}</span>}
        </td>
        <td>
          {t.detail.actions[track.action]}
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

function Fonts({ attached, present }: { attached: string[]; present: string[] }) {
  const t = useT();
  if (attached.length === 0 && present.length === 0) return null;
  return (
    <div className="fonts">
      {attached.length > 0 && (
        <p>
          <span className="muted">{t.detail.attachedFonts}</span>
          {attached.join(", ")}
        </p>
      )}
      {present.length > 0 && (
        <p>
          <span className="muted">{t.detail.presentFonts}</span>
          {present.join(", ")}
        </p>
      )}
    </div>
  );
}
