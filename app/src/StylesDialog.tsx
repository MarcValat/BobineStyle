import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import { exportStyles, getFonts, importStyles } from "./api";
import { Dialog, DialogHeader } from "./Dialog";
import { Select } from "./Dropdown";
import { useT } from "./i18n";
import { InfoTip } from "./InfoTip";
import { HOUSE_STYLE, saveListStyle, saveStyles, useListStyle, useStyles, useStylesError, type SubtitleStyle } from "./styles";
import { errorMessage, FIELD_PROPS } from "./util";
import "./StylesDialog.css";

type VariantKey = "italic" | "top" | "dashes" | "overlap" | "margins";

/** "Modifier les styles…": the house style (built in, duplicable) and the
 * user's own -- each one's dialogue look, its variants on or off and what
 * they change, a sample of its text -- and which one the list uses. Kept
 * only with "Enregistrer". */
export function StylesDialog({ onClose }: { onClose: () => void }) {
  const t = useT();
  const s = t.styles;
  const saved = useStyles();
  // The user's styles couldn't be read (styles.json damaged): said, and
  // saving writes them anew.
  const loadError = useStylesError();
  const listStyle = useListStyle();
  const [draft, setDraft] = useState<SubtitleStyle[]>(saved);
  // The style shown: its index in `draft`, -1 the house style.
  const [shown, setShown] = useState(() => saved.findIndex((style) => style.name === listStyle));
  // The list's style, by index (-1 the house style): kept by index while
  // a style's name is being typed.
  const [listIndex, setListIndex] = useState(() => saved.findIndex((style) => style.name === listStyle));
  const [fonts, setFonts] = useState<string[]>([]);
  const [variant, setVariant] = useState<"top" | "overlap" | "margins" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getFonts()
      .then(setFonts)
      .catch(() => {});
  }, []);

  const style = shown >= 0 ? draft[shown] : HOUSE_STYLE;
  const house = shown < 0;
  const problem = checkStyles(draft, t);

  function update(patch: Partial<SubtitleStyle>) {
    if (house) return;
    setDraft((d) => d.map((item, i) => (i === shown ? { ...item, ...patch } : item)));
  }

  /** Adds `style` under a name no other style has, and shows it. */
  function add(style: SubtitleStyle) {
    setDraft((d) => {
      const next = [...d, { ...style, name: freeName(style.name, d) }];
      setShown(next.length - 1);
      return next;
    });
  }

  function remove() {
    if (house) return;
    setDraft((d) => d.filter((_, i) => i !== shown));
    if (listIndex === shown) setListIndex(-1);
    else if (listIndex > shown) setListIndex(listIndex - 1);
    setShown(-1);
  }

  async function importFile() {
    setError(null);
    const path = await open({ title: s.importTitle, filters: [{ name: s.fileFilter, extensions: ["json"] }] });
    if (typeof path !== "string") return;
    try {
      const imported = await importStyles(path);
      setDraft((d) => {
        let next = [...d];
        for (const item of imported) next = [...next, { ...HOUSE_STYLE, ...item, name: freeName(item.name, next) }];
        if (imported.length > 0) setShown(d.length);
        return next;
      });
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function exportFile() {
    setError(null);
    const path = await save({ title: s.exportTitle, defaultPath: s.fileName, filters: [{ name: s.fileFilter, extensions: ["json"] }] });
    if (!path) return;
    try {
      await exportStyles(path, draft);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function keep() {
    setSaving(true);
    setError(null);
    try {
      const trimmed = draft.map((item) => ({ ...item, name: item.name.trim(), font: item.font.trim() }));
      await saveStyles(trimmed);
      saveListStyle(listIndex >= 0 ? trimmed[listIndex].name : "");
      onClose();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  const variants: { key: VariantKey; on: boolean; change: ReactNode; edit?: "top" | "overlap" | "margins" }[] = [
    { key: "italic", on: style.italic_variant, change: style.italic ? s.upright : s.inItalic },
    { key: "top", on: style.top_variant, change: s.atTop(style.top_margin), edit: "top" },
    { key: "dashes", on: style.dashes_variant, change: s.dashesBlock },
    {
      key: "overlap",
      on: style.overlap_variant,
      change: (
        <>
          <span className="style-swatch" style={{ background: style.overlap_color }} />
          {s.otherColor}
        </>
      ),
      edit: "overlap",
    },
    { key: "margins", on: style.margins_variant, change: s.widerMargins(style.margins_extra), edit: "margins" },
  ];

  return (
    <Dialog onClose={onClose} fill className="styles-panel" labelledBy="styles-title">
      <DialogHeader id="styles-title" title={s.title} onClose={onClose}>
        <span className="styles-subtitle">{s.subtitle}</span>
      </DialogHeader>

      <div className="styles-body">
        <nav className="styles-list" aria-label={s.title}>
          {[HOUSE_STYLE, ...draft].map((item, i) => (
            <button
              key={i}
              className={`styles-item${i - 1 === shown ? " selected" : ""}`}
              aria-current={i - 1 === shown || undefined}
              onClick={() => setShown(i - 1)}
            >
              <span className="styles-item-sample" style={sampleLook(item, 0.2)}>
                Aa
              </span>
              <span className="styles-item-text">
                <span className="styles-item-name">{item.name || s.house}</span>
                <span className="styles-item-detail">{i === 0 ? s.provided(item) : s.short(item)}</span>
              </span>
              {i - 1 === listIndex && <span className="list-badge list-badge-ready">{s.listDefault}</span>}
            </button>
          ))}
          <button className="styles-new" onClick={() => add({ ...HOUSE_STYLE, name: s.newName })}>
            {s.newStyle}
          </button>
          <span className="styles-list-space" />
          <div className="styles-list-actions">
            <button className="small-button" onClick={() => add({ ...style, name: s.copyName(style.name || s.house) })}>
              {s.duplicate}
            </button>
            <button className="small-button styles-delete" disabled={house} onClick={remove}>
              {s.remove}
            </button>
          </div>
          <div className="styles-list-actions">
            <button className="small-button" onClick={importFile}>
              {s.import}
            </button>
            <button className="small-button" disabled={draft.length === 0} onClick={exportFile}>
              {s.export}
            </button>
          </div>
          <p className="styles-list-note">{s.houseNote}</p>
        </nav>

        <div className="styles-form list-scroll">
          <div className="styles-form-head">
            <label className="styles-field">
              <span className="lbl">{s.name}</span>
              <input
                {...FIELD_PROPS}
                type="text"
                value={house ? s.house : style.name}
                disabled={house}
                onChange={(e) => update({ name: e.target.value })}
              />
            </label>
            <label className="check-row">
              <input type="checkbox" checked={listIndex === shown} onChange={(e) => setListIndex(e.target.checked ? shown : -1)} />
              {s.useForList}
            </label>
          </div>

          <section className="styles-section">
            <h3>{s.dialogue}</h3>
            <div className="styles-grid">
              <div className="styles-set">
                <span className="lbl">{s.font}</span>
                <Select
                  label={s.font}
                  value={style.font}
                  options={[...new Set([style.font, ...fonts])].map((font) => ({ value: font, label: font }))}
                  onChange={(font) => update({ font })}
                  disabled={house}
                />
                <span className="styles-hint">{s.attached}</span>
              </div>
              <NumberField label={s.size} value={style.size} unit="px" disabled={house} onChange={(size) => update({ size })} />
              <div className="styles-set">
                <span className="lbl">{s.weight}</span>
                <span className="styles-toggles">
                  <button
                    className={`small-button styles-toggle${style.bold ? " on" : ""}`}
                    aria-pressed={style.bold}
                    disabled={house}
                    onClick={() => update({ bold: !style.bold })}
                  >
                    <b>{s.bold}</b>
                  </button>
                  <button
                    className={`small-button styles-toggle${style.italic ? " on" : ""}`}
                    aria-pressed={style.italic}
                    disabled={house}
                    onClick={() => update({ italic: !style.italic })}
                  >
                    <i>{s.italic}</i>
                  </button>
                </span>
              </div>
              <ColorField label={s.color} value={style.color} disabled={house} onChange={(color) => update({ color })} />
              <ColorField
                label={s.outline}
                value={style.outline_color}
                disabled={house}
                onChange={(outline_color) => update({ outline_color })}
                width={{ label: s.outlineWidth, value: style.outline, onChange: (outline) => update({ outline }) }}
              />
              <ColorField
                label={s.shadow}
                value={style.shadow_color}
                disabled={house}
                onChange={(shadow_color) => update({ shadow_color })}
                width={{ label: s.shadowDistance, value: style.shadow, onChange: (shadow) => update({ shadow }) }}
              />
              <NumberField
                label={s.marginBottom}
                value={style.margin_bottom}
                unit="px"
                disabled={house}
                onChange={(margin_bottom) => update({ margin_bottom })}
              />
              <NumberField
                label={s.marginSide}
                value={style.margin_side}
                unit="px"
                disabled={house}
                onChange={(margin_side) => update({ margin_side })}
              />
            </div>
          </section>

          <section className="styles-section">
            <h3>
              {s.variants} <InfoTip>{s.variantsHint}</InfoTip>
            </h3>
            <div className="tracks-table-wrap">
              <table className="styles-variants">
                <thead>
                  <tr>
                    <th>{s.variant}</th>
                    <th>{s.forWhat}</th>
                    <th>{s.changes}</th>
                    <th className="styles-variant-on">{s.on}</th>
                  </tr>
                </thead>
                <tbody>
                  {variants.map((v) => (
                    <tr key={v.key} className={v.on ? "" : "dim"}>
                      <td className="styles-variant-name">{s.variantNames[v.key]}</td>
                      <td className="muted">{s.variantFor[v.key]}</td>
                      <td>
                        <span className="styles-variant-change">
                          <span>{v.change}</span>
                          {v.edit && (
                            <button className="small-button" disabled={house || !v.on} onClick={() => setVariant(v.edit!)}>
                              {s.editVariant}
                            </button>
                          )}
                        </span>
                      </td>
                      <td className="styles-variant-on">
                        <input
                          type="checkbox"
                          checked={v.on}
                          disabled={house}
                          aria-label={s.variantOn(s.variantNames[v.key])}
                          onChange={(e) => update({ [`${v.key}_variant`]: e.target.checked } as Partial<SubtitleStyle>)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="styles-section">
            <h3>
              {s.sample} <span className="styles-hint">{s.sampleHint}</span>
            </h3>
            <div className="styles-sample">
              <span style={sampleLook(style, 0.32)}>{s.sampleLine}</span>
              <span style={sampleLook({ ...style, italic: style.italic_variant ? !style.italic : style.italic }, 0.32)}>
                {s.sampleItalic}
              </span>
            </div>
          </section>
        </div>
      </div>

      <div className="styles-footer">
        <span className="styles-hint">{error ?? problem ?? loadError ?? s.signsKept}</span>
        <span className="styles-footer-space" />
        <button onClick={onClose}>{t.common.cancel}</button>
        <button className="primary-button" disabled={!!problem || saving} onClick={keep}>
          {s.save}
        </button>
      </div>

      {variant && !house && <VariantDialog variant={variant} style={style} onChange={update} onClose={() => setVariant(null)} />}
    </Dialog>
  );
}

/** A variant's "Modifier": only what it changes. */
function VariantDialog({
  variant,
  style,
  onChange,
  onClose,
}: {
  variant: "top" | "overlap" | "margins";
  style: SubtitleStyle;
  onChange: (patch: Partial<SubtitleStyle>) => void;
  onClose: () => void;
}) {
  const s = useT().styles;
  return (
    <Dialog onClose={onClose} closeOnBackdrop className="styles-variant-panel" labelledBy="variant-title">
      <DialogHeader id="variant-title" title={s.variantNames[variant]} onClose={onClose} />
      {variant === "top" && (
        <NumberField label={s.topMargin} value={style.top_margin} unit="px" onChange={(top_margin) => onChange({ top_margin })} />
      )}
      {variant === "overlap" && (
        <ColorField label={s.overlapColor} value={style.overlap_color} onChange={(overlap_color) => onChange({ overlap_color })} />
      )}
      {variant === "margins" && (
        <NumberField
          label={s.marginsExtra}
          value={style.margins_extra}
          unit="px"
          onChange={(margins_extra) => onChange({ margins_extra })}
        />
      )}
    </Dialog>
  );
}

/** A number in pixels of a 1080p screen. */
function NumberField({
  label,
  value,
  unit,
  disabled = false,
  onChange,
}: {
  label: string;
  value: number;
  unit: string;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <label className="styles-set">
      <span className="lbl">{label}</span>
      <span className="styles-number">
        <input
          {...FIELD_PROPS}
          type="number"
          min={0}
          step={0.5}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <span className="lbl">{unit}</span>
      </span>
    </label>
  );
}

/** A color (a swatch picking it, its "#RRGGBB" typed), with an outline's
 * width or a shadow's distance beside it (`width`). */
function ColorField({
  label,
  value,
  disabled = false,
  onChange,
  width,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  width?: { label: string; value: number; onChange: (value: number) => void };
}) {
  const [typed, setTyped] = useState(value);
  useEffect(() => setTyped(value), [value]);
  return (
    <div className={width ? "styles-set styles-set-wide" : "styles-set"}>
      <span className="lbl">{label}</span>
      <span className="styles-color">
        <input
          type="color"
          value={value.toLowerCase()}
          disabled={disabled}
          aria-label={label}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
        />
        <input
          {...FIELD_PROPS}
          type="text"
          className="styles-hex"
          value={typed}
          disabled={disabled}
          aria-label={label}
          onChange={(e) => {
            setTyped(e.target.value);
            if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) onChange(e.target.value.toUpperCase());
          }}
        />
        {width && (
          <span className="styles-number">
            <input
              {...FIELD_PROPS}
              type="number"
              min={0}
              step={0.5}
              value={width.value}
              disabled={disabled}
              aria-label={width.label}
              title={width.label}
              onChange={(e) => width.onChange(Number(e.target.value))}
            />
            <span className="lbl">px</span>
          </span>
        )}
      </span>
    </div>
  );
}

/** A style's text as CSS, at `scale` of a 1080p screen: the sample, the
 * list's "Aa". */
function sampleLook(style: SubtitleStyle, scale: number): CSSProperties {
  const outline = style.outline * scale * 2;
  const shadow = style.shadow * scale;
  return {
    fontFamily: `"${style.font}", sans-serif`,
    fontSize: `${style.size * scale}px`,
    fontWeight: style.bold ? 700 : 400,
    fontStyle: style.italic ? "italic" : "normal",
    color: style.color,
    WebkitTextStroke: outline > 0 ? `${outline}px ${style.outline_color}` : undefined,
    paintOrder: "stroke fill",
    textShadow: shadow > 0 ? `${shadow}px ${shadow}px 0 ${style.shadow_color}` : undefined,
  };
}

/** `name`, or "name 2", "name 3"… when another style has it. */
function freeName(name: string, styles: SubtitleStyle[]): string {
  const taken = new Set(styles.map((s) => s.name.trim()));
  let candidate = name.trim();
  for (let n = 2; taken.has(candidate); n++) candidate = `${name.trim()} ${n}`;
  return candidate;
}

/** What keeps the styles from being saved, if anything. */
function checkStyles(styles: SubtitleStyle[], t: ReturnType<typeof useT>): string | null {
  const names = styles.map((s) => s.name.trim());
  if (names.some((n) => !n)) return t.styles.nameMissing;
  if (new Set(names).size < names.length) return t.styles.nameTaken;
  if (styles.some((s) => !(s.size >= 1 && s.size <= 400))) return t.styles.sizeWrong;
  return null;
}
