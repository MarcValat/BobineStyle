import { useEffect, useId, useRef, useState } from "react";
import { Dialog, DialogHeader } from "./Dialog";
import { useT } from "./i18n";

/** A job's progress log behind a "Journal (n)" link: the raw "[analyse] ..."
 * lines are useful when something's wrong, but shouldn't take screen space
 * -- unfolded in place, they pushed the layout around. Opens in a dialog
 * that follows new lines as they come. */
export function LogPanel({ lines }: { lines: string[] }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  if (lines.length === 0) return null;
  return (
    <>
      <button className="small-button log-button" onClick={() => setOpen(true)}>
        {t.common.log(lines.length)}
      </button>
      {open && <LogDialog lines={lines} onClose={() => setOpen(false)} />}
    </>
  );
}

function LogDialog({ lines, onClose }: { lines: string[]; onClose: () => void }) {
  const t = useT();
  const id = useId();
  const logRef = useRef<HTMLPreElement>(null);
  // Kept scrolled to the latest line, unless the user scrolled up to read.
  const following = useRef(true);
  useEffect(() => {
    const log = logRef.current;
    if (log && following.current) log.scrollTop = log.scrollHeight;
  }, [lines]);
  return (
    <Dialog onClose={onClose} closeOnBackdrop className="log-dialog" labelledBy={id}>
      <DialogHeader id={id} title={t.common.log(lines.length)} onClose={onClose} />
      <pre
        ref={logRef}
        className="log"
        onScroll={(e) => {
          const el = e.currentTarget;
          following.current = el.scrollHeight - el.scrollTop - el.clientHeight < 8;
        }}
      >
        {lines.join("\n")}
      </pre>
    </Dialog>
  );
}
