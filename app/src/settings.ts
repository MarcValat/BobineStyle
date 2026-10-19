import { useSyncExternalStore } from "react";
import { loadSetting, saveSetting } from "./util";

// Options' settings, remembered across sessions; a view using one follows
// a change made in Options right away. From Bobine Audio.
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function changed(): void {
  listeners.forEach((listener) => listener());
}

const CHECK_UPDATES_KEY = "bobinestyle.checkUpdates";

/** Whether the app looks for an update on GitHub at startup (the default). */
function loadCheckUpdates(): boolean {
  return loadSetting(CHECK_UPDATES_KEY) !== "0";
}

export function saveCheckUpdates(check: boolean): void {
  saveSetting(CHECK_UPDATES_KEY, check ? null : "0");
  changed();
}

export function useCheckUpdates(): boolean {
  return useSyncExternalStore(subscribe, loadCheckUpdates);
}

const LIST_COLLAPSED_KEY = "bobinestyle.listCollapsed";

/** Whether the file list is folded to a narrow column. */
function loadListCollapsed(): boolean {
  return loadSetting(LIST_COLLAPSED_KEY) === "1";
}

export function saveListCollapsed(collapsed: boolean): void {
  saveSetting(LIST_COLLAPSED_KEY, collapsed ? "1" : null);
  changed();
}

export function useListCollapsed(): boolean {
  return useSyncExternalStore(subscribe, loadListCollapsed);
}

const RECURSIVE_KEY = "bobinestyle.recursive";

/** Whether a folder added brings its subfolders' MKVs too (its seasons):
 * on by default. */
export function loadRecursive(): boolean {
  return loadSetting(RECURSIVE_KEY) !== "0";
}

export function saveRecursive(recursive: boolean): void {
  saveSetting(RECURSIVE_KEY, recursive ? null : "0");
  changed();
}

export function useRecursive(): boolean {
  return useSyncExternalStore(subscribe, loadRecursive);
}
