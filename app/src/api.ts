// Client for the engine sidecar (engine/src/bobinestyle/server.py).
import { engineReady, getEngineUrl } from "./engine";

export interface PlannedTrack {
  index: number;
  codec: string;
  language: string | null;
  title: string | null;
  french: boolean;
  /** French tracks: "full" or "forced". */
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
  audio: { language: string | null; title: string | null; french: boolean } | null;
  tracks: PlannedTrack[];
  fonts: string[];
  fonts_present: string[];
  fonts_missing: string[];
  warnings: string[];
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
  const resp = await fetch(`${await getEngineUrl()}${path}`, init);
  if (!resp.ok) {
    let detail: unknown = `Erreur ${resp.status}`;
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

export async function planFile(path: string): Promise<Plan> {
  return (await postJson("/plan", { path })).json();
}

export async function startMux(source: string, output: string): Promise<string> {
  return (await (await postJson("/jobs/mux", { source, output })).json()).job_id;
}

export async function cancelJob(jobId: string): Promise<void> {
  await postJson(`/jobs/${jobId}/cancel`, {});
}

type JobEvent<T> =
  | { type: "log"; message: string }
  | { type: "progress"; value: number }
  | { type: "done"; result: T }
  | { type: "error"; message: string }
  | { type: "cancelled" };

export class JobCancelled extends Error {
  constructor() {
    super("Annulé");
  }
}

/** A job as a promise: `onProgress` gets how far it got (0 to 1), `onStart`
 * its id (to cancel it); settles with its result, its error, or
 * JobCancelled. An unexpected close (engine crash) is an error. */
export function runJob<T>(
  jobId: Promise<string>,
  onProgress: (value: number) => void,
  onStart?: (id: string) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    Promise.all([jobId, getEngineUrl()])
      .then(([id, url]) => {
        onStart?.(id);
        const ws = new WebSocket(`${url.replace("http", "ws")}/jobs/${id}/ws`);
        let finished = false;
        ws.onmessage = (msg) => {
          const event = JSON.parse(msg.data) as JobEvent<T>;
          if (event.type === "progress") onProgress(event.value);
          else if (event.type === "done") resolve(event.result);
          else if (event.type === "error") reject(new Error(event.message));
          else if (event.type === "cancelled") reject(new JobCancelled());
          if (event.type !== "log" && event.type !== "progress") finished = true;
        };
        ws.onclose = () => {
          if (!finished) reject(new Error("Le moteur s'est arrêté pendant la tâche."));
        };
      })
      .catch(reject);
  });
}
