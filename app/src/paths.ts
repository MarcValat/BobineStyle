/** Just the filename, for display -- callers keep the full path around
 * separately (e.g. as a `title` tooltip) for when it's actually needed. */
export function basename(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

/** The name of the folder a file is in ("Saison 1"): the list's groups. */
export function parentName(path: string): string {
  const parts = path.split(/[\\/]/);
  return parts.length > 1 ? parts[parts.length - 2] : "";
}
