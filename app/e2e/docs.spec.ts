// The docs' screenshots (docs/screenshots), on the demo series
// (e2e/make_demo.py: synthetic, nothing copyrighted): a season read, the
// first episode's plan shown, and the Styles dialog on a style of one's
// own, in both languages and themes, at 1440x900 as Bobine Audio's and
// Subs'. Only when asked:
//   DOCS=1 npx playwright test e2e/docs.spec.ts
// The demo goes to C:\Users\Public\Videos on Windows (the output path the
// shots show names no one's folder), next to the tests' media elsewhere;
// DEMO_DIR to put it somewhere else.
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { HOUSE_STYLE } from "../src/styles";
import { putStyles } from "./engine";
import { expect, test, type App } from "./fixtures";
import { home, MEDIA_DIR } from "./media";

const DEMO_DIR = process.env.DEMO_DIR ?? (process.platform === "win32" ? "C:/Users/Public/Videos" : join(MEDIA_DIR, "demo"));
const SHOTS = fileURLToPath(new URL("../../docs/screenshots", import.meta.url));
const SEASON = `${DEMO_DIR}/Les Phares du Nord/Saison 1`.replaceAll("\\", "/");
const EPISODES = ["S01E01", "S01E02", "S01E03", "Bonus"].map((n) => encodeURIComponent(`${SEASON}/Les Phares du Nord - ${n}.mkv`));

test.skip(!process.env.DOCS, "the docs' screenshots: DOCS=1 to take them");

test.beforeAll(() => {
  execFileSync("uv", ["run", "--project", "../engine", "python", "e2e/make_demo.py", DEMO_DIR], {
    stdio: "inherit",
    shell: process.platform === "win32",
  });
});

/** The pointer out of the way, the transitions done, then the shot. */
async function shoot(app: App, name: string) {
  await app.page.mouse.move(1439, 899);
  await app.page.waitForTimeout(600);
  await app.page.screenshot({ path: join(SHOTS, `${name}.png`) });
}

for (const language of ["fr", "en"] as const)
  for (const theme of ["light", "dark"] as const) {
    test(`${language} ${theme}`, async ({ app }) => {
      const { page } = app;
      const fr = language === "fr";
      await page.emulateMedia({ colorScheme: theme });
      await page.addInitScript(
        ([language, theme]) => {
          localStorage.setItem("bobinestyle.language", language);
          localStorage.setItem("bobinestyle.theme", theme);
          localStorage.setItem("bobinestyle.languages", "fre,eng");
          localStorage.setItem("bobinestyle.defaultLanguage", "fre");
        },
        [language, theme],
      );
      const suffix = `${language}-${theme}`;

      // The season read, the first episode's plan shown.
      await page.goto(home(`&files=${EPISODES.join("|")}&windowControls=1`));
      await app.allRead();
      await shoot(app, `main-${suffix}`);

      // A style of one's own, in Styles.
      await putStyles([{ ...HOUSE_STYLE, name: fr ? "Cinéma jaune" : "Cinema yellow", size: 72, color: "#FFE066" }]);
      await page.reload();
      await app.allRead();
      await page.getByRole("button", { name: fr ? "Modifier les styles…" : "Edit styles…" }).click();
      const dialog = page.getByRole("dialog", { name: "Styles" });
      await dialog.locator(".styles-item").nth(1).click();
      await expect(dialog.getByRole("textbox", { name: fr ? "Nom" : "Name" })).toHaveValue(/jaune|yellow/);
      await shoot(app, `styles-${suffix}`);
    });
  }
