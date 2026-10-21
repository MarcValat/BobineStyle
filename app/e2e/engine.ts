// The engine, asked directly by the tests (not through the page): the
// styles it keeps, and what a written file holds.
import { execFileSync } from "node:child_process";
import type { SubtitleStyle } from "../src/styles";
import { ENGINE_PORT } from "./media";

const ENGINE = `http://127.0.0.1:${ENGINE_PORT}`;
// The dev builds' token (see playwright.config.ts).
const HEADERS = { "X-Bobine-Token": "bobine-dev", "Content-Type": "application/json" };

/** Keeps `styles` as the user's (the engine's styles.json). */
export async function putStyles(styles: SubtitleStyle[]): Promise<void> {
  const resp = await fetch(`${ENGINE}/styles`, { method: "PUT", headers: HEADERS, body: JSON.stringify({ styles }) });
  if (!resp.ok) throw new Error(`styles: ${resp.status} ${await resp.text()}`);
}

/** The user's styles, as the engine keeps them. */
export async function getStyles(): Promise<SubtitleStyle[]> {
  const resp = await fetch(`${ENGINE}/styles`, { headers: HEADERS });
  if (!resp.ok) throw new Error(`styles: ${resp.status} ${await resp.text()}`);
  return (await resp.json()).styles;
}

interface WrittenSubtitle {
  language: string | null;
  title: string | null;
  codec: string;
  default: boolean;
  forced: boolean;
  text: string;
}

export interface WrittenFile {
  subtitles: WrittenSubtitle[];
  /** The attached fonts' file names. */
  fonts: string[];
}

const READ = `
import json, sys
from bobinestyle.ffmpeg_backend import extract_subtitle_text, probe_streams, subtitle_streams
path = sys.argv[1]
streams = probe_streams(path)
print(json.dumps({
    "subtitles": [
        {"language": s.language, "title": s.title, "codec": s.codec, "default": s.default, "forced": s.forced,
         "text": extract_subtitle_text(path, s.index, s.codec)}
        for s in subtitle_streams(streams)
    ],
    "fonts": [s.filename for s in streams if s.kind == "Attachment"],
}))
`;

/** What `path`'s subtitle tracks are, and hold, read by the engine's ffmpeg. */
export function readMkv(path: string): WrittenFile {
  return JSON.parse(execFileSync("uv", ["run", "--project", "../engine", "python", "-c", READ, path], { encoding: "utf8" }));
}

/** An ASS script's style `name`, its fields by the Format line's names
 * ("Fontname", "Fontsize", "PrimaryColour"...). */
export function assStyle(text: string, name: string): Record<string, string> {
  const format = /^Format:\s*(Name,.*)$/m
    .exec(text)?.[1]
    .split(",")
    .map((f) => f.trim());
  const line = text.split("\n").find((l) => l.startsWith(`Style: ${name},`));
  if (!format || !line) throw new Error(`no style ${name} in:\n${text.slice(0, 600)}`);
  const values = line.slice("Style: ".length).split(",");
  return Object.fromEntries(format.map((field, i) => [field, values[i]?.trim() ?? ""]));
}
