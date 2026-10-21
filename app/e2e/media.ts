import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** Where e2e/make_media.py writes the media (ignored by git). */
export const MEDIA_DIR = fileURLToPath(new URL("media", import.meta.url));

/** The tests' engine's data folder (its styles.json): never the app's. */
export const DATA_DIR = join(tmpdir(), "bobine-style-e2e-data");

/** The tests' own engine and Vite (see playwright.config.ts): never the
 * app's (`tauri dev`: 8758 and 1420), nor Bobine Audio's or Subs' (theirs:
 * 8756 / 8757, tests 8766 / 1431 and 8758 / 1430). */
export const ENGINE_PORT = 8769;
export const APP_PORT = 1433;

/** The app's page, pointed at the tests' engine, with more dev `params`
 * (see util.ts devParam), e.g. "&windowControls=1". */
export const home = (params = "") => `/?enginePort=${ENGINE_PORT}${params}`;

/** A media file's full path, with forward slashes (as the dev URLs take it). */
const media = (name: string) => `${MEDIA_DIR}/${name}`.replaceAll("\\", "/");

// What make_media.py puts in them: the tests check the plans against it.
export const E01 = media("Show - E01.mkv"); // jpn audio; fre full ASS, fre forced ASS, eng SRT
export const E02 = media("Show - E02.mkv"); // fre audio; fre full ASS, fre forced ASS
export const E03 = media("Show - E03.mkv"); // jpn audio; eng SRT, ger ASS: no French
export const E04 = media("Show - E04.mkv"); // jpn audio, no subtitles

/** The dev URL (see StyleBatch's `files`) listing `files`. */
export const filesUrl = (...files: string[]) => home(`&files=${files.map(encodeURIComponent).join("|")}`);
