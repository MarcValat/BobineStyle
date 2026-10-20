// Client for the engine sidecar (engine/src/bobinestyle/server.py).
import { engineHeaders, engineReady, getEngineToken, getEngineUrl } from "./engine";
import { t } from "./i18n";

export interface PlannedTrack {
  index: number;
  codec: string;
  /** Its language (ISO 639-2, "fra" made "fre"; guessed from its title
   * when untagged). */
  language: string | null;
  title: string | null;
  /** In one of the chosen languages: restyled and named. */
  chosen: boolean;
  /** Chosen tracks: "full" or "forced". */
  kind: "full" | "forced" | null;
  new_title: string | null;
  default: boolean;
  forced: boolean;
  /** "restyle": ASS in the house style; "convert": SRT made ASS; "copy": untouched. */
  action: "restyle" | "convert" | "copy";
  dialogue_lines: number | null;
  notes: string[];
}

export interface Plan {
  path: string;
  video_size: [number, number] | null;
  /** `same`: in the default subtitles' language (their forced track is the default). */
  audio: { language: string | null; title: string | null; same: boolean } | null;
  tracks: PlannedTrack[];
  fonts: string[];
  fonts_present: string[];
  fonts_missing: string[];
  warnings: string[];
  default_language: string | null;
}

/** The subtitles' languages to restyle, and the one whose track becomes
 * the default (null: the first). */
export interface Languages {
  languages: string[];
  default_language: string | null;
}

export interface Output {
  path: string;
  exists: boolean;
}

export interface MuxResult {
  path: string;
  plan: Plan;
}

async function engineFetch(path: string, init?: RequestInit): Promise<Response> {
  await engineReady();
  const headers = new Headers(init?.headers);
  for (const [name, value] of Object.entries(await engineHeaders())) headers.set(name, value);
  const resp = await fetch(`${await getEngineUrl()}${path}`, { ...init, headers });
  if (!resp.ok) {
    let detail: unknown = t().common.httpError(resp.status);
    try {
      detail = (await resp.json()).detail ?? detail;
    } catch {
      // not JSON: keep the status
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return resp;
}

function postJson(path: string, body: unknown): Promise<Response> {
  return engineFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** Picked or dropped paths as MKV files, a folder standing for its MKVs
 * (its seasons too when `recursive`), never a previous run's Output. */
export async function expandPaths(paths: string[], recursive: boolean): Promise<string[]> {
  return (await (await postJson("/paths/expand", { paths, recursive })).json()).files;
}

/** Where each file goes (Output/ next to it, or `folder`), and whether
 * something is already there. */
export async function planOutputs(sources: string[], folder: string | null): Promise<Output[]> {
  return (await (await postJson("/outputs", { sources, folder })).json()).outputs;
}

/** The language of the engine's messages (plan notes, job logs, errors). */
export async function setEngineLanguage(language: string): Promise<void> {
  await engineFetch(`/language`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ language }),
  });
}

export async function planFile(path: string, languages: Languages): Promise<Plan> {
  return (await postJson("/plan", { path, ...languages })).json();
}

export async function startMux(source: string, output: string, languages: Languages): Promise<string> {
  return (await (await postJson("/jobs/mux", { source, output, ...languages })).json()).job_id;
}

export async function cancelJob(jobId: string): Promise<void> {
  await postJson(`/jobs/${jobId}/cancel`, {});
}

export type JobEvent<TResult> =
  | { type: "log"; message: string }
  | { type: "progress"; value: number }
  | { type: "done"; result: TResult }
  | { type: "error"; message: string }
  | { type: "cancelled" };

/** Follows a job over its WebSocket: every event goes to `onEvent`; a
 * connection lost before the job ended (the engine crashed) as an error.
 * From Bobine Audio. */
export async function connectJobWS<TResult>(jobId: string, onEvent: (event: JobEvent<TResult>) => void): Promise<() => void> {
  // A WebSocket takes no header: the token goes in its address.
  const token = encodeURIComponent(await getEngineToken());
  const ws = new WebSocket(`${(await getEngineUrl()).replace("http", "ws")}/jobs/${jobId}/ws?token=${token}`);
  let settled = false;

  ws.onmessage = (ev) => {
    const event: JobEvent<TResult> = JSON.parse(ev.data);
    if (event.type === "done" || event.type === "error" || event.type === "cancelled") settled = true;
    onEvent(event);
  };
  ws.onerror = () => {
    if (!settled) {
      settled = true;
      onEvent({ type: "error", message: t().common.websocketLost });
    }
  };
  ws.onclose = () => {
    if (!settled) {
      settled = true;
      onEvent({ type: "error", message: t().common.connectionLost });
    }
  };
  return () => ws.close();
}
