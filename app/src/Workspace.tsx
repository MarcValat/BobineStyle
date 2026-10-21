import { useEffect, useRef, useState, type ReactNode } from "react";
import { moved } from "./batchShared";
import { shortcutKey } from "./util";
import { useT } from "./i18n";
import { ArrowDownIcon, ArrowUpIcon, CloseIcon, FoldIcon, WarningIcon } from "./icons";
import { Tooltip } from "./InfoTip";
import { saveListCollapsed } from "./settings";
import "./Workspace.css";

/** The workspace with no file yet: what the app does, its drop zone, and
 * anything under them (what it brings). From Bobine Audio. */
export function EmptyWorkspace({ title, hint, children }: { title: string; hint: string; children: ReactNode }) {
  return (
    <section className="empty-workspace">
      <div className="empty-workspace-intro">
        <h1>{title}</h1>
        <p>{hint}</p>
      </div>
      {children}
    </section>
  );
}

/** "Tout retirer", in a list's header: at once while nothing would be lost,
 * otherwise asking first, on a line under the header (`results`: analyses
 * or edits would go with the files). Escape keeps them. */
export function RemoveAllButton({ results, disabled, onRemove }: { results: boolean; disabled: boolean; onRemove: () => void }) {
  const t = useT();
  const [asking, setAsking] = useState(false);
  const confirm = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!asking) return;
    confirm.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setAsking(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [asking]);
  return (
    <>
      <button
        className={`small-button${asking ? " icon-button-on" : ""}`}
        disabled={disabled}
        aria-expanded={results ? asking : undefined}
        onClick={() => (results ? setAsking(!asking) : onRemove())}
      >
        {t.common.removeAll}
      </button>
      {asking && (
        <div className="remove-all-confirm" role="alertdialog" aria-label={t.common.removeAllQuestion}>
          <span>{t.common.removeAllQuestion}</span>
          <button
            ref={confirm}
            className="small-button export-cancel"
            disabled={disabled}
            onClick={() => {
              setAsking(false);
              onRemove();
            }}
          >
            {t.common.removeAll}
          </button>
          <button className="small-button" onClick={() => setAsking(false)}>
            {t.common.keep}
          </button>
        </div>
      )}
    </>
  );
}

/** How a list row's badge is tinted: where its file stands (see rowState),
 * or a warning for one that needs checking. */
export type BadgeKind = "idle" | "queued" | "running" | "ready" | "done" | "error" | "warning";

/** One file of the workspace's list: its name (the full path on hover),
 * a line saying what's used of it, and a badge saying where it stands, with
 * a colored bar at its left. Clicking it shows it in the detail; its own
 * buttons (move, remove) show on hover, focus and selection. */
export function ListRow({
  name,
  path,
  detail,
  className = "",
  state,
  badge,
  badgeKind,
  badgeAlert = badgeKind === "warning",
  progress,
  selected,
  onSelect,
  actions,
}: {
  name: ReactNode;
  /** On hover: the full path. */
  path: string;
  detail: ReactNode;
  /** A look of its own. */
  className?: string;
  /** rowState's value, for the bar. */
  state: string;
  badge: string;
  badgeKind: BadgeKind;
  /** The warning sign before it (default: a warning badge's). */
  badgeAlert?: boolean;
  /** How far its processing got (0 to 1), as a bar under its name. */
  progress?: number;
  selected: boolean;
  onSelect: () => void;
  actions?: ReactNode;
}) {
  const row = useRef<HTMLLIElement>(null);
  // Selected (by a click, or ↑ ↓ -- see useListKeys): in view, and the
  // focus follows it when it was on another row.
  useEffect(() => {
    if (!selected || !row.current) return;
    row.current.scrollIntoView({ block: "nearest" });
    const focused = document.activeElement;
    if (focused?.classList.contains("list-row-main") && row.current.parentElement?.contains(focused)) {
      row.current.querySelector<HTMLElement>(".list-row-main")?.focus();
    }
  }, [selected]);
  return (
    <li ref={row} className={`list-row list-row-state-${state}${selected ? " selected" : ""} ${className}`}>
      <button className="list-row-main" onClick={onSelect} aria-current={selected || undefined} title={path}>
        <span className="list-row-bar" />
        <span className="list-row-text">
          <span className="list-row-name">{name}</span>
          {progress === undefined ? (
            <span className="list-row-detail">{detail}</span>
          ) : (
            <span className="list-row-progress" aria-hidden="true">
              <span style={{ width: `${Math.round(progress * 100)}%` }} />
            </span>
          )}
        </span>
        <span className="list-row-status">
          <span className={`list-badge list-badge-${badgeKind}`}>
            {badgeAlert && <WarningIcon />}
            {badge}
          </span>
        </span>
      </button>
      {actions && <span className="list-row-actions">{actions}</span>}
    </li>
  );
}

// How long the column takes to slide (Workspace.css's .list-folding).
const FOLD_MS = 220;
let foldTimer: number | undefined;

/** Folds or unfolds the list, its column sliding to the new width -- only
 * then: the column's width follows the window's, and a resize of the window
 * mustn't trail behind. */
function foldList(collapsed: boolean) {
  const root = document.documentElement;
  root.classList.add("list-folding");
  window.clearTimeout(foldTimer);
  foldTimer = window.setTimeout(() => root.classList.remove("list-folding"), FOLD_MS + 50);
  saveListCollapsed(collapsed);
}

/** The list header's button folding the list to a narrow column (names and
 * states only, for a small window) or unfolding it; remembered, the same
 * useListCollapsed. */
export function FoldButton({ collapsed }: { collapsed: boolean }) {
  const t = useT();
  const label = collapsed ? t.common.unfoldList : t.common.foldList;
  return (
    <Tooltip text={label}>
      <button
        className={`small-button icon-small-button fold-button${collapsed ? " folded" : ""}`}
        aria-label={label}
        aria-expanded={!collapsed}
        onClick={() => foldList(!collapsed)}
      >
        <FoldIcon />
      </button>
    </Tooltip>
  );
}

/** ↑ ↓ select the previous or next row of a shown list (`enabled`), from
 * anywhere in the window but a field, a drop-down or a dialog. */
export function useListKeys(enabled: boolean, count: number, index: number, onSelect: (index: number) => void): void {
  const latest = useRef({ count, index, onSelect });
  latest.current = { count, index, onSelect };
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.key !== "ArrowUp" && e.key !== "ArrowDown") || !shortcutKey(e) || document.querySelector(".dialog-overlay")) return;
      const { count, index, onSelect } = latest.current;
      const next = index + (e.key === "ArrowDown" ? 1 : -1);
      e.preventDefault();
      if (next >= 0 && next < count) onSelect(next);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled]);
}

/** A row's ↑ ↓ ✕: moves it within the list, or drops it. Icons, not
 * characters: a font's arrows sit off-center in a button (and Windows may
 * draw them as emoji). */
export function MoveButtons({
  count,
  index,
  disabled,
  onChange,
}: {
  count: number;
  index: number;
  disabled: boolean;
  onChange: (update: <T>(items: T[]) => T[]) => void;
}) {
  const t = useT();
  return (
    <>
      <Tooltip text={t.batch.moveUp}>
        <button
          className="small-button icon-small-button"
          onClick={() => onChange((f) => moved(f, index, index - 1))}
          disabled={disabled || index === 0}
          aria-label={t.batch.moveUp}
        >
          <ArrowUpIcon />
        </button>
      </Tooltip>
      <Tooltip text={t.batch.moveDown}>
        <button
          className="small-button icon-small-button"
          onClick={() => onChange((f) => moved(f, index, index + 1))}
          disabled={disabled || index === count - 1}
          aria-label={t.batch.moveDown}
        >
          <ArrowDownIcon />
        </button>
      </Tooltip>
      <Tooltip text={t.common.remove}>
        <button
          className="small-button icon-small-button"
          onClick={() => onChange((f) => f.filter((_, i) => i !== index))}
          disabled={disabled}
          aria-label={t.common.remove}
        >
          <CloseIcon />
        </button>
      </Tooltip>
    </>
  );
}
