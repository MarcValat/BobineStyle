import { open } from "@tauri-apps/plugin-dialog";
import { loadSetting, saveSetting } from "./util";
import { t } from "./i18n";

// From Bobine Audio: the system's dialogs, starting in the folder the last
// pick came from.
const LAST_FOLDER_KEY = "bobinestyle.lastFolder";

// None remembered: the dialog opens wherever the system puts it.
function lastFolder(): string | undefined {
  return loadSetting(LAST_FOLDER_KEY) ?? undefined;
}

function rememberFolder(path: string, isFolder = false): void {
  if (isFolder) {
    saveSetting(LAST_FOLDER_KEY, path);
    return;
  }
  const cut = Math.max(path.lastIndexOf("\\"), path.lastIndexOf("/"));
  if (cut > 0) saveSetting(LAST_FOLDER_KEY, path.slice(0, cut));
}

/** The system's open dialog for MKV files. */
export async function pickMediaFiles(): Promise<string[] | null> {
  const selected = await open({
    title: t().add.files,
    multiple: true,
    filters: [{ name: t().add.mkvFilter, extensions: ["mkv"] }],
    defaultPath: lastFolder(),
  });
  if (!selected) return null;
  const files = Array.isArray(selected) ? selected : [selected];
  if (files.length > 0) rememberFolder(files[0]);
  return files;
}

/** The system's folder picker for folders to add (a season, a series). */
export async function pickFolders(): Promise<string[] | null> {
  const selected = await open({ title: t().add.folderDialog, directory: true, multiple: true, defaultPath: lastFolder() });
  if (!selected) return null;
  const folders = Array.isArray(selected) ? selected : [selected];
  if (folders.length > 0) rememberFolder(folders[0], true);
  return folders;
}

/** The system's folder picker, starting at `defaultPath` when given. */
export async function pickFolder(defaultPath?: string | null): Promise<string | null> {
  const selected = await open({ title: t().output.folderDialog, directory: true, defaultPath: defaultPath ?? lastFolder() });
  return typeof selected === "string" ? selected : null;
}
