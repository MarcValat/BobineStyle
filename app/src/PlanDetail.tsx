import { revealItemInDir } from "@tauri-apps/plugin-opener";
import type { PlannedTrack } from "./api";
import { fileName, languageName, type FileItem } from "./shared";

/** Everything processing one file does: each subtitle track's fate, the
 * default track and why, the fonts. */
export default function PlanDetail({ file }: { file: FileItem }) {
  const plan = file.plan;
  return (
    <section className="card detail">
      <div className="detail-head">
        <h2 title={file.path}>{fileName(file.path)}</h2>
        {plan?.video_size && (
          <span className="muted">
            {plan.video_size[0]}×{plan.video_size[1]}
          </span>
        )}
      </div>
      {file.status === "planning" && <p className="muted">Lecture des pistes…</p>}
      {file.error && <p className="error">{file.error}</p>}
      {plan && !plan.tracks.some((t) => t.french) && (
        <p className="muted">
          {plan.tracks.length === 0 ? "Aucune piste de sous-titres" : "Aucune piste de sous-titres française"} : ce fichier ne sera pas traité.
        </p>
      )}
      {plan && plan.tracks.some((t) => t.french) && (
        <>
          <p>
            {plan.audio ? (
              <>
                Audio par défaut en <strong>{languageName(plan.audio.language)}</strong>
                {plan.audio.title && <span className="muted"> ({plan.audio.title})</span>} : sous-titres{" "}
                <strong>{plan.audio.french ? "forcés" : "complets"}</strong> par défaut.
              </>
            ) : (
              <>Pas d'audio : sous-titres complets par défaut.</>
            )}
          </p>
          <table className="tracks">
            <thead>
              <tr>
                <th>Piste</th>
                <th>Devient</th>
                <th>Marquage</th>
                <th>Traitement</th>
              </tr>
            </thead>
            <tbody>
              {plan.tracks.map((t) => (
                <TrackRow key={t.index} track={t} />
              ))}
            </tbody>
          </table>
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
          <span className="muted">Sortie</span>
          <span className="path" title={file.output.path}>
            {file.output.path}
          </span>
          {file.output.exists && (
            <button className="link" onClick={() => revealItemInDir(file.output!.path)}>
              Afficher
            </button>
          )}
        </div>
      )}
    </section>
  );
}

const ACTIONS = { restyle: "Style maison", convert: "SRT converti en ASS", copy: "Copiée telle quelle" };

function TrackRow({ track: t }: { track: PlannedTrack }) {
  const current = [languageName(t.language), t.codec, t.title && `« ${t.title} »`].filter(Boolean).join(" · ");
  return (
    <>
      <tr className={t.french ? "" : "dim"}>
        <td>
          <span className="muted">#{t.index}</span> {current}
        </td>
        <td>{t.french ? t.new_title : <span className="muted">inchangée</span>}</td>
        <td>
          {t.default && <span className="pill accent">défaut</span>}
          {t.forced && <span className="pill">forcés</span>}
        </td>
        <td>
          {ACTIONS[t.action]}
          {t.dialogue_lines !== null && <span className="muted"> · {t.dialogue_lines} répliques</span>}
        </td>
      </tr>
      {t.notes.length > 0 && (
        <tr className="notes">
          <td colSpan={4}>
            {t.notes.map((n) => (
              <span key={n} className="note">
                {n}
              </span>
            ))}
          </td>
        </tr>
      )}
    </>
  );
}

function Fonts({ attached, present }: { attached: string[]; present: string[] }) {
  if (attached.length === 0 && present.length === 0) return null;
  return (
    <div className="fonts">
      {attached.length > 0 && (
        <p>
          <span className="muted">Polices jointes : </span>
          {attached.join(", ")}
        </p>
      )}
      {present.length > 0 && (
        <p>
          <span className="muted">Déjà dans le MKV : </span>
          {present.join(", ")}
        </p>
      )}
    </div>
  );
}
