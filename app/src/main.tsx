import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LanguageProvider } from "./i18n";
import { applyTheme, loadTheme } from "./theme";
import { engineReady } from "./engine";
import { startUiScale } from "./uiScale";
import { blockBrowserFeatures } from "./browserKeys";
// Inter, bundled: the same text on Windows and Linux, no network needed.
import "@fontsource-variable/inter";
import "@fontsource-variable/inter/wght-italic.css";

// Before the first render, so a forced theme never flashes the other one.
applyTheme(loadTheme());

// Wait for the engine from the start: the UI is usable meanwhile, its
// requests go through once it answers (see engine.ts).
engineReady().catch(() => {});

// No browser right-click menu nor browser shortcuts in the compiled app
// (import.meta.env.DEV is Vite's own dev-vs-build flag): see browserKeys.ts.
if (!import.meta.env.DEV) blockBrowserFeatures();

// The interface at its size before the first render, so it never shows at
// another one first.
startUiScale()
  .catch(() => {})
  .finally(() =>
    ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
      <React.StrictMode>
        <LanguageProvider>
          <App />
        </LanguageProvider>
      </React.StrictMode>,
    ),
  );
