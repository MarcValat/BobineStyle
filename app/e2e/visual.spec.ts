// The main screens compared to screenshots recorded earlier on this system
// (e2e/__screenshots__/<platform>, not in git: fonts and rendering differ
// between systems). The first run records them; after a wanted change,
// `npm run test:e2e -- e2e/visual.spec.ts --update-snapshots` records them
// again.
import { expect, test } from "./fixtures";
import { E01, E02, E03, filesUrl, home } from "./media";

for (const theme of ["dark", "light"] as const) {
  test.describe(theme, () => {
    test.beforeEach(async ({ app }) => {
      await app.page.emulateMedia({ colorScheme: theme });
    });

    test("empty workspace", async ({ app }) => {
      await app.page.goto(home("&windowControls=1"));
      await expect(app.page).toHaveScreenshot(`empty-${theme}.png`);
    });

    test("files read", async ({ app }) => {
      await app.page.goto(`${filesUrl(E01, E02, E03)}&windowControls=1`);
      await app.allRead();
      await app.page.mouse.move(1, 1);
      // The output's folder is the media's, wherever they are.
      await expect(app.page).toHaveScreenshot(`files-${theme}.png`, { mask: [app.page.locator(".detail-path")] });
    });

    test("styles", async ({ app }) => {
      await app.page.goto(`${filesUrl(E01)}&windowControls=1`);
      await app.page.getByRole("button", { name: "Modifier les styles…" }).click();
      await app.page.waitForTimeout(500);
      await expect(app.page).toHaveScreenshot(`styles-${theme}.png`);
    });

    test("settings", async ({ app }) => {
      await app.page.goto(home("&windowControls=1"));
      await app.page.getByRole("button", { name: "Paramètres" }).click();
      await app.page.waitForTimeout(500);
      // The version changes from one release to the next.
      await expect(app.page).toHaveScreenshot(`settings-${theme}.png`, { mask: [app.page.getByText(/Version actuelle/)] });
    });
  });
}
