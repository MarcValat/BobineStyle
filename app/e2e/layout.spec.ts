// Every screen audited (see audit.ts) at the smallest window and a usual
// one, in both themes and both languages: what's found is listed by screen.
// Written files go to a temporary folder, removed after.
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { inspect } from "./audit";
import { expect, test } from "./fixtures";
import { E01, E02, E03, E04, filesUrl, home } from "./media";

/** Found, and known: awaiting a decision, not to fail the run meanwhile. */
const KNOWN: RegExp[] = [];

const SIZES = [
  [1024, 640],
  [1440, 900],
] as const;

for (const [width, height] of SIZES)
  for (const theme of ["dark", "light"] as const)
    for (const language of ["fr", "en"] as const) {
      test(`${width}x${height} ${theme} ${language}`, async ({ app }) => {
        test.setTimeout(240_000);
        const { page } = app;
        await page.setViewportSize({ width, height });
        await page.emulateMedia({ colorScheme: theme });
        const outDir = mkdtempSync(join(tmpdir(), "bobine-style-e2e-out-"));
        await page.addInitScript(
          ([language, theme, outDir]) => {
            localStorage.setItem("bobinestyle.language", language);
            localStorage.setItem("bobinestyle.theme", theme);
            localStorage.setItem("bobinestyle.outputDir", outDir);
          },
          [language, theme, outDir.replaceAll("\\", "/")],
        );
        const fr = language === "fr";
        const found: string[] = [];
        /** `screen` reached by `reach`, the pointer out of the way, audited. */
        const audit = async (screen: string, reach: () => Promise<unknown>) => {
          await reach();
          await page.mouse.move(width - 1, height - 1);
          await page.waitForTimeout(450); // transitions done
          for (const [kind, what] of await inspect(page)) {
            const finding = `${screen}: ${kind} -- ${what}`;
            if (!KNOWN.some((known) => known.test(finding))) found.push(finding);
          }
        };
        const escape = () => page.keyboard.press("Escape").then(() => page.waitForTimeout(400));

        await audit("empty", () => page.goto(home("&windowControls=1")));
        await audit("files read", async () => {
          await page.goto(`${filesUrl(E01, E02, E03, E04)}&windowControls=1`);
          await app.allRead();
        });
        await audit("languages picker open", () => app.setting(fr ? "Langues :" : "Languages:").click());
        await escape();
        await audit("row hovered", () => app.rows().nth(1).hover());
        await audit("a file done", async () => {
          await page.getByRole("button", { name: fr ? "Appliquer à ce fichier" : "Apply to this file" }).click();
          await expect(app.rows().first().locator(".list-badge")).toHaveText(fr ? "Terminé" : "Done", { timeout: 120_000 });
        });
        await audit("a file with nothing to do", () => app.rows().nth(3).locator(".list-row-main").click());
        await audit("output", () => page.getByRole("button", { name: fr ? "Modifier…" : "Change…" }).click());
        await escape();
        await audit("list folded", () => page.locator(".fold-button:visible").click());
        await page.locator(".fold-button:visible").click();
        await audit("styles", () => page.getByRole("button", { name: fr ? "Modifier les styles…" : "Edit styles…" }).click());
        await audit("a style of one's own", () => page.getByRole("button", { name: fr ? "Dupliquer" : "Duplicate" }).click());
        await audit("variant", () =>
          page
            .getByRole("dialog", { name: "Styles" })
            .getByRole("button", { name: fr ? "Modifier" : "Edit", exact: true })
            .first()
            .click(),
        );
        await escape();
        await escape();
        await audit("settings", () => page.getByRole("button", { name: fr ? "Paramètres" : "Settings" }).click());
        await escape();

        rmSync(outDir, { recursive: true, force: true });
        expect(found).toEqual([]);
      });
    }
