import { connectJobWS } from "./api";
import { t } from "./i18n";

/** An engine job (a remux) as a promise: `onLog` gets its messages,
 * `onStart` its id as soon as it's known (to cancel it), `onProgress` how
 * far it got (0 to 1), and it settles with its result, its error, or
 * JobCancelled. From Bobine Audio. */
export function runJob<T>(
  jobId: Promise<string>,
  onLog: (message: string) => void,
  onStart?: (id: string) => void,
  onProgress?: (value: number) => void,
): Promise<T> {
  return new Promise((resolve, reject) => {
    jobId
      .then((id) => {
        onStart?.(id);
        return connectJobWS<T>(id, (event) => {
          if (event.type === "log") onLog(event.message);
          else if (event.type === "progress") onProgress?.(event.value);
          else if (event.type === "done") resolve(event.result);
          else if (event.type === "error") reject(new Error(event.message));
          else if (event.type === "cancelled") reject(new JobCancelled());
        });
      })
      .catch(reject);
  });
}

/** What runJob rejects with when the job was cancelled (see cancelJob). */
export class JobCancelled extends Error {
  constructor() {
    super(t().common.cancelled);
  }
}
