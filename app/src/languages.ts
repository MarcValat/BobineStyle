import { t } from "./i18n";

/** The languages offered while no file is read yet. */
export const USUAL_LANGUAGES = ["fre", "eng", "ger", "spa", "ita", "por", "jpn"];

/** A language code's name in the UI's language, as Matroska tags tracks
 * (ISO 639-2); a code it doesn't know as is. From Bobine Audio. */
export function languageName(code: string | null): string {
  return code ? (t().languages.names[code] ?? code) : t().languages.unknown;
}
