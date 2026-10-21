import { useEffect } from "react";
import { setEngineLanguage } from "./api";
import { OptionsButton } from "./Options";
// The app's own icon, the same as the window's and the installer's.
import logoUrl from "../src-tauri/icons/128x128.png";
import { StyleBatch } from "./StyleBatch";
import { UpdateButton } from "./UpdateButton";
import "./App.css";
import { useLanguage } from "./i18n";
import { EngineStatusBadge } from "./EngineStatus";
import { WindowControls } from "./WindowControls";

/** The window: the top bar (the engine's state, updates, settings) over
 * the workspace. One file dropped works as well as a whole series. From
 * Bobine Audio. */
function App() {
  // The engine's messages (plan notes, job logs, errors) in the UI's
  // language whenever it changes (engine.ts sends it once the engine is up).
  const language = useLanguage();
  useEffect(() => {
    setEngineLanguage(language).catch(() => {});
  }, [language]);

  return (
    <div className="container">
      {/* The window's title bar (no system one: see WindowControls): dragged
          by its free parts, where data-tauri-drag-region is -- the bar and
          the name, not their children's buttons. */}
      <div className="top-bar" data-tauri-drag-region>
        <span className="app-brand" data-tauri-drag-region>
          <img src={logoUrl} alt="" />
          Bobine Style
        </span>
        <div className="top-actions">
          <EngineStatusBadge />
          <UpdateButton />
          <OptionsButton />
        </div>
        <WindowControls />
      </div>

      <StyleBatch />
    </div>
  );
}

export default App;
