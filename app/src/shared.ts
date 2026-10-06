import type { Output, Plan } from "./api";

/** Where one file stands, from being read to being written. */
export type FileStatus =
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
}

/** Can be (re)processed: French subtitles, not busy, and its output free
 * unless `force`. */
export function isRunnable(file: FileItem, force: boolean): boolean {
  const planned = ["ready", "done", "error", "cancelled"].includes(file.status);
  return planned && file.output !== undefined && (force || !file.output.exists);
}

export function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

const LANGUAGES: Record<string, string> = {
  fre: "français",
  fra: "français",
  eng: "anglais",
  jpn: "japonais",
  spa: "espagnol",
  ger: "allemand",
  deu: "allemand",
  ita: "italien",
  por: "portugais",
  kor: "coréen",
  chi: "chinois",
  zho: "chinois",
};

export function languageName(code: string | null): string {
  return code ? (LANGUAGES[code] ?? code) : "langue inconnue";
}

export function errorMessage(e: unknown): string {
  return String(e instanceof Error ? e.message : e);
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
