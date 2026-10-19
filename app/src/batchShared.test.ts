import { describe, expect, it } from "vitest";
import { isAlreadyDone, isRedoable, isRunnable, limiter, rowState, type FileItem } from "./batchShared";

const file = (status: FileItem["status"], exists?: boolean): FileItem => ({
  path: "D:/Séries/S01E01.mkv",
  status,
  output: exists === undefined ? undefined : { path: "D:/Séries/Output/S01E01.mkv", exists },
});

describe("which files the buttons process", () => {
  it("redoes a read file that isn't busy", () => {
    for (const status of ["ready", "done", "error", "cancelled"] as const) expect(isRedoable(file(status, false))).toBe(true);
    for (const status of ["planning", "no_french", "plan_error", "queued", "running"] as const)
      expect(isRedoable(file(status, false))).toBe(false);
  });

  it("needs to know where the file goes", () => {
    expect(isRedoable(file("ready"))).toBe(false);
  });

  it("skips a file already written, unless asked to redo it", () => {
    expect(isRunnable(file("ready", false), false)).toBe(true);
    expect(isRunnable(file("ready", true), false)).toBe(false);
    expect(isRunnable(file("ready", true), true)).toBe(true);
  });
});

describe("a row's bar", () => {
  it("shows a file already written as done, unless it's to be redone", () => {
    expect(isAlreadyDone(file("ready", true), false)).toBe(true);
    expect(rowState(file("ready", true), false)).toBe("done");
    expect(rowState(file("ready", true), true)).toBe("ready");
  });

  it("follows the file through its processing", () => {
    expect(rowState(file("planning"), false)).toBe("queued");
    expect(rowState(file("queued", false), false)).toBe("queued");
    expect(rowState(file("running", false), false)).toBe("running");
    expect(rowState(file("done", true), false)).toBe("done");
    expect(rowState(file("error", false), false)).toBe("error");
    expect(rowState(file("plan_error"), false)).toBe("error");
    expect(rowState(file("no_french"), false)).toBe("idle");
  });
});

describe("limiter", () => {
  it("runs at most n at a time, in order", async () => {
    const limit = limiter(2);
    let running = 0;
    let most = 0;
    const started: number[] = [];
    const task = (i: number) => async () => {
      started.push(i);
      most = Math.max(most, ++running);
      await new Promise((r) => setTimeout(r, 5));
      running--;
      return i;
    };
    const results = await Promise.all([0, 1, 2, 3, 4].map((i) => limit(task(i))));
    expect(results).toEqual([0, 1, 2, 3, 4]);
    expect(started).toEqual([0, 1, 2, 3, 4]);
    expect(most).toBe(2);
  });

  it("goes on after a failure", async () => {
    const limit = limiter(1);
    const failed = limit(() => Promise.reject(new Error("no")));
    await expect(failed).rejects.toThrow("no");
    await expect(limit(() => Promise.resolve("next"))).resolves.toBe("next");
  });
});
