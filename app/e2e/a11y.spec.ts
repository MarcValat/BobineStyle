// Accessibility (axe-core, WCAG 2.1 A and AA rules): the main screens and
// dialogs, in both themes. Fails on serious and critical findings; color
// contrast is layout.spec.ts's (it measures what axe can't: text over
// translucent panels).
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type App } from "./fixtures";
import { E01, E02, E04, filesUrl, home } from "./media";

async function axe(app: App, screen: string, found: string[]) {
  await app.page.mouse.move(1, 1);
  await app.page.waitForTimeout(450);
  const { violations } = await new AxeBuilder({ page: app.page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .disableRules(["color-contrast"])
    .analyze();
  for (const v of violations)
    if (v.impact === "serious" || v.impact === "critical")
      found.push(
        `${screen}: ${v.id} (${v.impact}) ${v.help} -- ${v.nodes
          .map((n) => n.target.join(" "))
          .slice(0, 3)
          .join(" | ")}`,
      );
}

for (const theme of ["dark", "light"] as const) {
  test(`screens and dialogs, ${theme}`, async ({ app }) => {
    test.setTimeout(240_000);
    const { page } = app;
    await page.emulateMedia({ colorScheme: theme });
    const found: string[] = [];
    const escape = () => page.keyboard.press("Escape").then(() => page.waitForTimeout(400));

    await page.goto(home("&windowControls=1"));
    await axe(app, "empty", found);
    await page.goto(`${filesUrl(E01, E02, E04)}&windowControls=1`);
    await app.allRead();
    await axe(app, "files read", found);
    await app.setting("Langues :").click();
    await axe(app, "languages picker", found);
    await escape();
    await page.getByRole("button", { name: "Modifier…" }).click();
    await axe(app, "output", found);
    await escape();
    await page.getByRole("button", { name: "Modifier les styles…" }).click();
    await axe(app, "styles", found);
    await page.getByRole("button", { name: "+ Nouveau style" }).click();
    await page.getByRole("dialog", { name: "Styles" }).getByRole("button", { name: "Modifier", exact: true }).first().click();
    await axe(app, "variant", found);
    await escape();
    await escape();
    await page.getByRole("button", { name: "Paramètres" }).click();
    await axe(app, "settings", found);

    expect(found).toEqual([]);
  });
}
