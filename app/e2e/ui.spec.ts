// The workspace's own behavior: the list (keys, order, removal, folding),
// the settings kept from one session to the next, the Styles dialog's
// rules, and a file that can't be read.
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { HOUSE_STYLE } from "../src/styles";
import { getStyles, putStyles } from "./engine";
import { expect, test, type App } from "./fixtures";
import { E01, E02, E03, filesUrl, home } from "./media";

const selected = (app: App) => app.page.locator(".list-row.selected");

test.describe("the list", () => {
  test.beforeEach(async ({ app }) => {
    await app.page.goto(filesUrl(E01, E02, E03));
    await expect(app.rows()).toHaveCount(3);
    await expect(app.page.getByRole("heading", { name: "Fichiers · 3" })).toBeVisible();
  });

  test("↑ ↓ move through the files", async ({ app }) => {
    await app.rows().first().locator(".list-row-main").click();
    await expect(selected(app)).toContainText("Show - E01.mkv");
    await app.page.keyboard.press("ArrowDown");
    await expect(selected(app)).toContainText("Show - E02.mkv");
    await app.page.keyboard.press("ArrowDown");
    await app.page.keyboard.press("ArrowDown");
    await expect(selected(app)).toContainText("Show - E03.mkv");
    await app.page.keyboard.press("ArrowUp");
    await expect(selected(app)).toContainText("Show - E02.mkv");
  });

  test("files move up and down, and leave", async ({ app }) => {
    // The row's buttons show on hover.
    const press = async (row: number, name: string) => {
      await app.rows().nth(row).hover();
      await app.rows().nth(row).getByRole("button", { name }).click();
    };
    await press(2, "Monter");
    await expect(app.rows().nth(1)).toContainText("Show - E03.mkv");
    await press(0, "Descendre");
    await expect(app.rows().nth(1)).toContainText("Show - E01.mkv");
    await press(1, "Retirer");
    await expect(app.rows()).toHaveCount(2);
    await expect(app.rows()).not.toContainText(["Show - E01.mkv"]);
  });

  test("Tout retirer empties the list", async ({ app }) => {
    await app.page.getByRole("button", { name: "Tout retirer" }).click();
    await expect(app.rows()).toHaveCount(0);
    await expect(app.page.getByText("Un style propre et lisible pour les sous-titres de tes MKV")).toBeVisible();
  });

  test("the folded list stays folded", async ({ app }) => {
    await app.page.getByRole("button", { name: "Replier la liste" }).click();
    await expect(app.page.getByRole("button", { name: "Déplier la liste" })).toBeVisible();
    await app.page.reload();
    await expect(app.page.getByRole("button", { name: "Déplier la liste" })).toBeVisible();
  });
});

test("the languages and the list's style are kept from one session to the next", async ({ app }) => {
  await putStyles([{ ...HOUSE_STYLE, name: "Jaune", color: "#FFE066" }]);
  await app.page.goto(filesUrl(E03));
  await app.allRead();
  await app.pick("Langues :", "Anglais");
  await app.pick("Sous-titres par défaut :", "Anglais");
  await app.pick("Style :", "Jaune");
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Prêt");

  await app.page.reload();
  await app.allRead();
  await expect(app.setting("Langues :")).toContainText("Français, Anglais");
  await expect(app.setting("Sous-titres par défaut :")).toContainText("Anglais");
  await expect(app.setting("Style :")).toContainText("Jaune");
  await expect(app.rows().first().locator(".list-badge")).toHaveText("Prêt");
});

test("the theme and the language are kept from one session to the next", async ({ app }) => {
  await app.page.goto(home());
  await app.page.getByRole("button", { name: "Paramètres" }).click();
  const settings = app.page.getByRole("dialog", { name: "Paramètres" });
  await settings.getByRole("tab", { name: "Clair" }).click();
  await expect(app.page.locator("html")).toHaveAttribute("data-theme", "light");
  await settings.getByRole("button", { name: "Langue" }).click();
  await app.page.getByRole("option", { name: "English" }).click();
  await expect(app.page.getByRole("dialog", { name: "Settings" })).toBeVisible();
  await app.page.keyboard.press("Escape");

  await app.page.reload();
  await expect(app.page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(app.page.getByRole("button", { name: "Settings" })).toBeVisible();
});

test("a file that can't be read says so, the others go on", async ({ app }) => {
  // The engine answers 400 to its plan.
  app.allowErrors(/HTTP 400 plan|status of 400/);
  const dir = mkdtempSync(join(tmpdir(), "bobine-style-e2e-bad-"));
  try {
    const bad = join(dir, "Not a video.mkv").replaceAll("\\", "/");
    writeFileSync(bad, "not a video");
    await app.page.goto(filesUrl(bad, E01));
    await expect(app.rows().first().locator(".list-badge")).toHaveText("Illisible");
    await expect(app.rows().nth(1).locator(".list-badge")).toHaveText("Prêt");
    await expect(app.footerPrimary()).toHaveText("Appliquer le style · 1 fichier");
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test.describe("the Styles dialog", () => {
  test.beforeEach(async ({ app }) => {
    await app.page.goto(filesUrl(E01));
    await app.page.getByRole("button", { name: "Modifier les styles…" }).click();
  });

  const dialog = (app: App) => app.page.getByRole("dialog", { name: "Styles" });

  test("the house style is shown, not changed", async ({ app }) => {
    const d = dialog(app);
    await expect(d.getByRole("textbox", { name: "Nom" })).toHaveValue("Style maison");
    await expect(d.getByRole("textbox", { name: "Nom" })).toBeDisabled();
    await expect(d.getByRole("button", { name: "Supprimer" })).toBeDisabled();
    await expect(d.getByRole("button", { name: "Exporter…" })).toBeDisabled();
    await expect(d.getByRole("checkbox", { name: "Italique active" })).toBeDisabled();
    await expect(d.getByRole("button", { name: "Modifier" }).first()).toBeDisabled();
  });

  test("a variant's Modifier shows only what it changes", async ({ app }) => {
    const d = dialog(app);
    await d.getByRole("button", { name: "+ Nouveau style" }).click();
    await d.getByRole("button", { name: "Modifier" }).first().click();
    const variant = app.page.getByRole("dialog", { name: "Haut de l'écran" });
    await expect(variant.getByRole("spinbutton")).toHaveCount(1);
    await variant.getByRole("spinbutton", { name: "Marge du haut" }).fill("40");
    await app.page.keyboard.press("Escape");
    await expect(variant).toBeHidden();
    await expect(d).toContainText("en haut, marge 40 px");
    // A variant turned off: nothing to change.
    await d.getByRole("checkbox", { name: "Haut de l'écran active" }).uncheck();
    await expect(d.getByRole("button", { name: "Modifier" }).first()).toBeDisabled();
  });

  test("each style needs a name of its own", async ({ app }) => {
    const d = dialog(app);
    const save = d.getByRole("button", { name: "Enregistrer" });
    await d.getByRole("button", { name: "+ Nouveau style" }).click();
    await d.getByRole("textbox", { name: "Nom" }).fill("");
    await expect(d).toContainText("Chaque style a besoin d'un nom.");
    await expect(save).toBeDisabled();
    await d.getByRole("button", { name: "Dupliquer" }).click();
    await d.getByRole("textbox", { name: "Nom" }).fill("A");
    await d.getByRole("button", { name: /^Aa/ }).nth(1).click();
    await d.getByRole("textbox", { name: "Nom" }).fill("A");
    await expect(d).toContainText("Deux styles ont le même nom.");
    await expect(save).toBeDisabled();
    await d.getByRole("textbox", { name: "Nom" }).fill("B");
    await save.click();
    await expect(d).toBeHidden();
    expect((await getStyles()).map((s) => s.name).sort()).toEqual(["A", "B"]);
  });

  test("Annuler keeps nothing; Supprimer, once saved, does", async ({ app }) => {
    const d = dialog(app);
    await d.getByRole("button", { name: "+ Nouveau style" }).click();
    await d.getByRole("button", { name: "Annuler" }).click();
    await expect(d).toBeHidden();
    expect(await getStyles()).toEqual([]);

    await putStyles([{ ...HOUSE_STYLE, name: "Gone" }]);
    await app.page.reload();
    await app.page.getByRole("button", { name: "Modifier les styles…" }).click();
    await d.getByRole("button", { name: /Gone/ }).click();
    await d.getByRole("button", { name: "Supprimer" }).click();
    await expect(d.getByRole("button", { name: /Gone/ })).toHaveCount(0);
    await d.getByRole("button", { name: "Enregistrer" }).click();
    expect(await getStyles()).toEqual([]);
  });
});
