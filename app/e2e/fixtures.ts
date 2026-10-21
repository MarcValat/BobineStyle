import { test as base, expect, type Page } from "@playwright/test";
import { existsSync, rmSync } from "node:fs";
import { putStyles } from "./engine";
import { MEDIA_DIR } from "./media";

/** What the engine's jobs answered, read from their WebSocket: each
 * processing's written file. */
class Jobs {
  readonly written: string[] = [];

  watch(page: Page) {
    page.on("websocket", (ws) =>
      ws.on("framereceived", ({ payload }) => {
        const event = JSON.parse(String(payload));
        if (event.type === "done" && event.result?.path) this.written.push(event.result.path);
      }),
    );
  }
}

/** What a test drives the app with: its page, and the usual gestures. */
export class App {
  readonly jobs = new Jobs();
  /** Errors a test causes on purpose (see allowErrors). */
  readonly allowed: RegExp[] = [];

  constructor(readonly page: Page) {
    this.jobs.watch(page);
  }

  /** Engine, page or console errors matching `pattern` don't fail the test:
   * it causes them on purpose (a file that can't be read...). */
  allowErrors(pattern: RegExp) {
    this.allowed.push(pattern);
  }

  rows() {
    return this.page.locator(".list-row");
  }

  /** The footer's gradient button (Appliquer le style…). */
  footerPrimary() {
    return this.page.locator(".batch-footer .primary-button");
  }

  /** Every listed file read (no "Lecture…" left). */
  async allRead() {
    await expect(this.rows().first()).toBeVisible();
    await expect(this.rows().filter({ hasText: /Lecture…|Reading…/ })).toHaveCount(0, { timeout: 60_000 });
  }

  /** A settings bar's dropdown (Langues, Sous-titres par défaut, Style). */
  setting(label: string | RegExp) {
    return this.page.locator(".batch-config").getByRole("button", { name: label });
  }

  /** Picks `options` in the dropdown `label` (several when it takes
   * several), closed after. */
  async pick(label: string, ...options: (string | RegExp)[]) {
    await this.setting(label).click();
    const list = this.page.getByRole("listbox", { name: label });
    for (const option of options) await list.getByRole("option", { name: option }).click();
    if (await list.isVisible()) await this.page.keyboard.press("Escape");
    await expect(list).toBeHidden();
  }
}

/** Every test starts with no styles of the user's, and fails on an engine
 * error (HTTP 4xx/5xx), a page error, a console error or a processed file
 * left next to the media, besides its own checks. */
export const test = base.extend<{ app: App }>({
  app: async ({ page }, use) => {
    await putStyles([]);
    const problems: string[] = [];
    page.on("response", async (r) => {
      if (r.status() >= 400) {
        const body = await r.text().catch(() => "");
        problems.push(`HTTP ${r.status()} ${r.url().split("?")[0].split("/").pop()} ${body.slice(0, 160)}`);
      }
    });
    page.on("pageerror", (e) => problems.push(`page error: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error" && !/favicon/.test(m.text())) problems.push(`console: ${m.text().slice(0, 200)}`);
    });
    const app = new App(page);
    await use(app);
    // Written next to the media (the output folder not set in time):
    // removed, and failed.
    const stray = existsSync(`${MEDIA_DIR}/Output`);
    rmSync(`${MEDIA_DIR}/Output`, { recursive: true, force: true });
    expect(stray, "files written next to the media").toBe(false);
    expect(
      problems.filter((p) => !app.allowed.some((pattern) => pattern.test(p))),
      "engine, page or console errors",
    ).toEqual([]);
  },
});

export { expect };
