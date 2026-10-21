// From start to finish: files listed, read (their tracks per language),
// processed -- each written file then read back: its subtitle tracks, their
// names and flags, the style in their scripts, the fonts attached. Written
// to a temporary folder, removed after.
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { HOUSE_STYLE } from "../src/styles";
import { assStyle, getStyles, putStyles, readMkv, type WrittenFile } from "./engine";
import { expect, test } from "./fixtures";
import { E01, E02, E03, E04, filesUrl } from "./media";

let outDir: string;

test.beforeEach(async ({ app }) => {
  outDir = mkdtempSync(join(tmpdir(), "bobine-style-e2e-out-"));
  await app.page.addInitScript((dir) => localStorage.setItem("bobinestyle.outputDir", dir), outDir.replaceAll("\\", "/"));
});

test.afterEach(() => rmSync(outDir, { recursive: true, force: true }));

/** The file written for `source`, read back. */
const written = (source: string): WrittenFile => readMkv(join(outDir, source.split("/").pop()!));

/** Each subtitle track: language, name, flags. */
const tracks = (file: WrittenFile) => file.subtitles.map((s) => [s.language, s.title, s.default, s.forced]);

test("the house style: the French tracks restyled and named, the default one picked by the audio", async ({ app }) => {
  await app.page.goto(filesUrl(E01, E02, E03, E04));
  await expect(app.rows()).toHaveCount(4);
  await app.allRead();

  // What each one will get, before anything is done.
  await expect(app.rows().nth(0)).toContainText("fre complets + forcés");
  await expect(app.rows().nth(2).locator(".list-badge")).toHaveText("Rien à faire");
  await expect(app.rows().nth(3).locator(".list-badge")).toHaveText("Rien à faire");
  await expect(app.page.locator(".detail-default")).toContainText(
    "Audio par défaut en japonais : sous-titres français complets par défaut.",
  );
  await expect(app.page.locator(".detail-style-scale")).toContainText("1280×720");
  await app.rows().nth(1).locator(".list-row-main").click();
  await expect(app.page.locator(".detail-default")).toContainText("Audio par défaut en français : sous-titres français forcés par défaut.");

  await expect(app.footerPrimary()).toHaveText("Appliquer le style · 2 fichiers");
  await app.footerPrimary().click();
  await expect(app.rows().locator(".list-badge").filter({ hasText: "Terminé" })).toHaveCount(2, { timeout: 120_000 });
  expect(app.jobs.written).toHaveLength(2);

  const e01 = written(E01);
  expect(tracks(e01)).toEqual([
    ["fre", "Français", true, false],
    ["fre", "Français (forcé)", false, true],
    ["eng", "English", false, false],
  ]);
  const dialogue = assStyle(e01.subtitles[0].text, "Default");
  expect([dialogue.Fontname, dialogue.PrimaryColour, dialogue.Bold]).toEqual(["Trebuchet MS", "&H00FFFFFF", "-1"]);
  expect(assStyle(e01.subtitles[0].text, "Italique").Italic).toBe("-1");
  // The signs keep their own look.
  expect(assStyle(e01.subtitles[1].text, "Sign").Fontname).toBe("Impact");
  // The English SRT, not chosen, copied as it is.
  expect(e01.subtitles[2].codec).toBe("subrip");
  expect(e01.fonts).toEqual(expect.arrayContaining(["trebuc.ttf", "trebucbd.ttf"]));

  expect(tracks(written(E02))).toEqual([
    ["fre", "Français", false, false],
    ["fre", "Français (forcé)", true, true],
  ]);
  // All done: no next step left.
  await expect(app.footerPrimary()).toHaveText("Appliquer le style");
  await expect(app.footerPrimary()).toBeDisabled();
});

test("other languages: English and German restyled in their own names, English by default", async ({ app }) => {
  await app.page.goto(filesUrl(E03));
  await app.allRead();
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Rien à faire");

  // The file's own languages offered first.
  await app.pick("Langues :", "Anglais", "Allemand");
  await app.pick("Sous-titres par défaut :", "Anglais");
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Prêt");

  await app.page.getByRole("button", { name: "Appliquer à ce fichier" }).click();
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Terminé", { timeout: 120_000 });
  const e03 = written(E03);
  expect(tracks(e03)).toEqual([
    ["eng", "English", true, false],
    ["ger", "Deutsch", false, false],
  ]);
  // The SRT converted, to take the style.
  expect(e03.subtitles[0].codec).toBe("ass");
  expect(assStyle(e03.subtitles[0].text, "Default").Fontname).toBe("Trebuchet MS");
});

test("a style of one's own, made in Styles, applied to the list", async ({ app }) => {
  await app.page.goto(filesUrl(E01));
  await app.allRead();
  await app.page.getByRole("button", { name: "Modifier les styles…" }).click();
  const dialog = app.page.getByRole("dialog", { name: "Styles" });
  // The house style can't be changed: duplicated.
  await expect(dialog.getByRole("textbox", { name: "Nom" })).toBeDisabled();
  await dialog.getByRole("button", { name: "Dupliquer" }).click();
  await dialog.getByRole("textbox", { name: "Nom" }).fill("Jaune");
  await dialog.locator(".styles-hex").first().fill("#FFE066");
  await dialog.getByRole("checkbox", { name: "Haut de l'écran active" }).uncheck();
  await dialog.getByRole("checkbox", { name: "Style de la liste" }).check();
  await dialog.getByRole("button", { name: "Enregistrer" }).click();
  await expect(dialog).toBeHidden();

  const kept = await getStyles();
  expect(kept.map((s) => [s.name, s.color, s.top_variant])).toEqual([["Jaune", "#FFE066", false]]);
  await expect(app.setting("Style :")).toContainText("Jaune");
  await expect(app.page.locator(".detail-style-summary")).toContainText("#FFE066");
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Prêt");

  await app.page.getByRole("button", { name: "Appliquer à ce fichier" }).click();
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Terminé", { timeout: 120_000 });
  const text = written(E01).subtitles[0].text;
  expect(assStyle(text, "Default").PrimaryColour).toBe("&H0066E0FF");
  expect(assStyle(text, "Italique").PrimaryColour).toBe("&H0066E0FF");
});

test("a file's own style, the others the list's", async ({ app }) => {
  await putStyles([{ ...HOUSE_STYLE, name: "Rouge", color: "#FF4040", font: "Arial", bold: false }]);
  await app.page.goto(filesUrl(E01, E02));
  await app.allRead();
  await app.rows().nth(1).locator(".list-row-main").click();
  await app.page.locator(".detail-style").getByRole("button", { name: "Style appliqué" }).click();
  await app.page.getByRole("option", { name: "Rouge" }).click();
  await expect(app.page.locator(".detail-style-summary")).toContainText("Arial 66 px · #FF4040");
  await expect(app.rows().nth(1).locator(".list-badge")).toHaveText("Prêt");

  await app.footerPrimary().click();
  await expect(app.rows().locator(".list-badge").filter({ hasText: "Terminé" })).toHaveCount(2, { timeout: 120_000 });
  expect(assStyle(written(E01).subtitles[0].text, "Default").Fontname).toBe("Trebuchet MS");
  const red = assStyle(written(E02).subtitles[0].text, "Default");
  expect([red.Fontname, red.PrimaryColour, red.Bold]).toEqual(["Arial", "&H004040FF", "0"]);
});
