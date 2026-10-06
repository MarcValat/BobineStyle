import { useEffect, useRef, useState } from "react";
import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWebview, type DragDropEvent } from "@tauri-apps/api/webview";
import "./FileDrop.css";

/** Paths dragged from the explorer onto the window, while `enabled`:
 * `onDrop` gets them as dropped (files and folders). While `blocked`, the
 * overlay says why and a drop does nothing. Returns whether a drag is over
 * the window, for DropOverlay. */
export function useFileDrop(enabled: boolean, blocked: string | null, onDrop: (paths: string[]) => void): boolean {
  const [dragging, setDragging] = useState(false);
  // The latest of each, without resubscribing on every render.
  const latest = useRef({ blocked, onDrop });
  latest.current = { blocked, onDrop };

  useEffect(() => {
    if (!enabled) return;
    function handle(event: DragDropEvent) {
      if (event.type === "leave") {
        setDragging(false);
      } else if (event.type === "enter" || event.type === "over") {
        setDragging(true);
      } else {
        setDragging(false);
        if (!latest.current.blocked && event.paths.length > 0) latest.current.onDrop(event.paths);
      }
    }

    // Dev only, in a plain browser: automated checks dispatch a
    // `bobinestyle:dragdrop` event carrying what Tauri would send.
    if (import.meta.env.DEV && !isTauri()) {
      const listener = (e: Event) => handle((e as CustomEvent<DragDropEvent>).detail);
      window.addEventListener("bobinestyle:dragdrop", listener);
      return () => {
        window.removeEventListener("bobinestyle:dragdrop", listener);
        setDragging(false);
      };
    }

    let unlisten: (() => void) | null = null;
    let gone = false;
    getCurrentWebview()
      .onDragDropEvent((e) => handle(e.payload))
      .then((u) => {
        if (gone) u();
        else unlisten = u;
      });
    return () => {
      gone = true;
      unlisten?.();
      setDragging(false);
    };
  }, [enabled]);

  return dragging;
}

/** What dropping would do, over the whole window. */
export function DropOverlay({
  dragging,
  blocked,
  label,
  hint,
}: {
  dragging: boolean;
  blocked: string | null;
  label: string;
  hint?: string;
}) {
  if (!dragging) return null;
  return (
    <div className="drop-overlay">
      <div className={`drop-zone ${blocked ? "drop-zone-blocked" : "drop-zone-active"}`}>
        <span className="drop-label">{blocked ?? label}</span>
        {!blocked && hint && <span className="drop-hint">{hint}</span>}
      </div>
    </div>
  );
}
