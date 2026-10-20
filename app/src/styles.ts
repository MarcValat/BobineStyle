import { useSyncExternalStore } from "react";
import { getStyles, putStyles } from "./api";
import { loadSetting, saveSetting } from "./util";

/** A subtitle style, as the engine takes it (engine/src/bobinestyle/
 * styles.py): sizes in pixels of a 1080p screen, colors "#RRGGBB", each
 * variant on or off with what it changes. */
export interface SubtitleStyle {
  name: string;
  font: string;
  size: number;
  bold: boolean;
  italic: boolean;
  color: string;
  outline_color: string;
  outline: number;
  shadow_color: string;
  shadow: number;
  margin_bottom: number;
  margin_side: number;
  italic_variant: boolean;
  top_variant: boolean;
  top_margin: number;
  dashes_variant: boolean;
  overlap_variant: boolean;
  overlap_color: string;
  margins_variant: boolean;
  margins_extra: number;
}

/** The house style, built in (the engine's HOUSE): not editable, it can
 * be duplicated. Its name is the UI's, in each language. */
export const HOUSE_STYLE: SubtitleStyle = {
  name: "",
  font: "Trebuchet MS",
  size: 66,
  bold: true,
  italic: false,
  color: "#FFFFFF",
  outline_color: "#000000",
  outline: 2.5,
  shadow_color: "#000000",
  shadow: 2.5,
  margin_bottom: 75,
  margin_side: 6,
  italic_variant: true,
  top_variant: true,
  top_margin: 75,
  dashes_variant: true,
  overlap_variant: true,
  overlap_color: "#FAEE8C",
  margins_variant: true,
  margins_extra: 45,
};

// The user's styles, read once from the engine (styles.json), and what
// went wrong reading or writing them.
let styles: SubtitleStyle[] = [];
let error: string | null = null;
let loaded: Promise<void> | null = null;
const listeners = new Set<() => void>();

function changed(): void {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Reads the user's styles from the engine, once. */
export function loadStyles(): Promise<void> {
  loaded ??= getStyles().then(
    (list) => {
      styles = list.map((s) => ({ ...HOUSE_STYLE, ...s }));
      error = null;
      changed();
    },
    (e) => {
      error = String(e instanceof Error ? e.message : e);
      loaded = null;
      changed();
    },
  );
  return loaded;
}

/** Keeps `next` as the user's styles (written by the engine). */
export async function saveStyles(next: SubtitleStyle[]): Promise<void> {
  await putStyles(next);
  styles = next;
  error = null;
  changed();
}

/** The user's own styles. */
export function useStyles(): SubtitleStyle[] {
  return useSyncExternalStore(subscribe, () => styles);
}

export function useStylesError(): string | null {
  return useSyncExternalStore(subscribe, () => error);
}

const LIST_STYLE_KEY = "bobinestyle.style";

/** The list's style, by name ("" the house style), remembered. */
function loadListStyle(): string {
  return loadSetting(LIST_STYLE_KEY) ?? "";
}

export function saveListStyle(name: string): void {
  saveSetting(LIST_STYLE_KEY, name || null);
  changed();
}

export function useListStyle(): string {
  return useSyncExternalStore(subscribe, loadListStyle);
}

/** The style named `name` ("" the house style); the house style when
 * it's gone (deleted). */
export function styleNamed(list: SubtitleStyle[], name: string): SubtitleStyle {
  return (name && list.find((s) => s.name === name)) || HOUSE_STYLE;
}
