// Foundations: design tokens with live contrast numbers, typography, and the app shell.
import { useMemo } from "react";
import pairsFile from "../../../src/styles/contrast-pairs.json";
import { formatRatio, hex, ratio, readToken, toRgb, type Rgb } from "../contrast";
import { Card, Icon, Lead } from "../parts";

/** light: Lumen; dark: Lumen in the panel's dark mode; night: the Lumen Dark theme. */
export type GalleryMode = "light" | "dark" | "night";

export const MODE_LABEL: Record<GalleryMode, string> = { light: "light mode", dark: "dark mode", night: "Lumen Dark" };

interface Pair {
  fg: string;
  bg: string;
  min: number;
  use: string;
  /** The modes the pair is drawn in (all three when absent). */
  modes?: string[];
}

const PAIRS: Pair[] = (pairsFile as { pairs: Pair[] }).pairs;

/** A pair colour is a token name or a literal #RRGGBB (docs/contrast.md). */
const isLiteral = (colour: string) => colour.startsWith("#");
const paint = (colour: string) => (isLiteral(colour) ? colour : `var(--lm-${colour})`);

const BRAND = [
  "lumen", "sky", "azure", "royal", "abyss", "night", "mint",
  "slate-700", "slate-500", "slate-300", "slate-100", "mist", "white",
  "verdant", "verdant-bright", "amber", "amber-bright", "ember", "ember-bright",
];

const SEMANTIC: { group: string; names: string[] }[] = [
  { group: "Surfaces", names: ["bg", "surface", "surface-raised", "surface-sunken", "surface-hover", "border", "border-control"] },
  { group: "Text and links", names: ["text", "text-strong", "text-2", "text-muted", "link", "link-hover"] },
  { group: "Primary and focus", names: ["primary", "primary-hover", "on-primary", "primary-tint", "on-primary-tint", "focus"] },
  {
    group: "States",
    names: [
      "success", "success-tint", "success-text", "warning", "warning-tint", "warning-text",
      "danger", "danger-tint", "danger-text", "info", "info-tint", "info-text",
    ],
  },
];

const SPACE = [1, 2, 3, 4, 5, 6, 7];
const RADII = ["s", "m", "l", "xl"];

function Swatch({ name, value, against }: { name: string; value: Rgb | null; against: Rgb | null }) {
  return (
    <li>
      <span className="gallery-swatch" style={{ background: `var(--lm-${name})` }} aria-hidden="true" />
      <code>--lm-{name}</code>
      <span className="has-text-grey">
        {value ? hex(value) : "…"}
        {value && against && <> · {formatRatio(ratio(value, against))} on surface</>}
      </span>
    </li>
  );
}

export function Tokens({ mode, styleTick }: { mode: GalleryMode; styleTick: number }) {
  // Recomputed whenever the mode or the loaded stylesheet changes.
  const values = useMemo(() => {
    void styleTick;
    const names = new Set([...BRAND, ...SEMANTIC.flatMap((g) => g.names), ...PAIRS.flatMap((p) => [p.fg, p.bg])]);
    const out: Record<string, Rgb | null> = {};
    for (const name of names) out[name] = isLiteral(name) ? toRgb(name) : readToken(name);
    return out;
  }, [mode, styleTick]);
  const surface = values.surface ?? null;
  const label = MODE_LABEL[mode];
  const rows = PAIRS.filter((p) => !p.modes || p.modes.includes(mode)).map((p) => {
    const fg = values[p.fg];
    const bg = values[p.bg];
    return { ...p, r: fg && bg ? ratio(fg, bg) : null };
  });
  const measured = rows.filter((r) => r.r !== null);
  const passed = measured.filter((r) => r.r! >= r.min).length;

  return (
    <>
      <Lead>
        Every colour is a <code>--lm-*</code> custom property. The values below are read from the stylesheet this page
        has loaded, in {label}, and every contrast ratio is computed here in the browser with the WCAG 2.x formula. The
        same table for light mode, dark mode and Lumen Dark is generated into <code>docs/contrast.md</code>.
      </Lead>
      <Card icon="palette" title="Brand colours (Luminare palette, the same in every mode)">
        <ul className="gallery-swatches">
          {BRAND.map((name) => (
            <Swatch key={name} name={name} value={values[name] ?? null} against={null} />
          ))}
        </ul>
      </Card>
      {SEMANTIC.map((g) => (
        <Card key={g.group} icon="palette" title={`${g.group} (${label})`}>
          <ul className="gallery-swatches">
            {g.names.map((name) => (
              <Swatch key={name} name={name} value={values[name] ?? null} against={name === "surface" ? null : surface} />
            ))}
          </ul>
        </Card>
      ))}
      <Card icon="table" title={`Contrast pairs: ${passed} of ${measured.length} pass in ${label}`}>
        <div className="table-container">
          <table className="table is-fullwidth is-striped">
            <caption className="has-text-left has-text-grey">
              Text needs 4.5:1 (WCAG 2.2, 1.4.3); control borders, focus rings and indicators need 3:1 (1.4.11).
            </caption>
            <thead>
              <tr>
                <th scope="col">Foreground</th>
                <th scope="col">Background</th>
                <th scope="col">Used for</th>
                <th scope="col" className="has-text-right">
                  Ratio
                </th>
                <th scope="col" className="has-text-right">
                  Needed
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.fg}|${row.bg}|${row.use}`}>
                  <td>
                    <span className="gallery-chip" style={{ background: paint(row.fg) }} aria-hidden="true" />
                    <code>{row.fg}</code>
                  </td>
                  <td>
                    <span className="gallery-chip" style={{ background: paint(row.bg) }} aria-hidden="true" />
                    <code>{row.bg}</code>
                  </td>
                  <td className="has-text-grey">{row.use}</td>
                  <td className="has-text-right has-ws-no-wrap">
                    {row.r === null ? (
                      "…"
                    ) : (
                      <>
                        {formatRatio(row.r)}{" "}
                        <span className={`tag ${row.r >= row.min ? "is-success" : "is-danger"}`}>{row.r >= row.min ? "pass" : "fail"}</span>
                      </>
                    )}
                  </td>
                  <td className="has-text-right">{row.min}:1</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <div className="columns">
        <div className="column">
          <Card icon="layout" title="Spacing (8px grid)">
            <ul className="gallery-scale">
              {SPACE.map((n) => (
                <li key={n}>
                  <code>--lm-space-{n}</code>
                  <span className="gallery-bar" style={{ inlineSize: `var(--lm-space-${n})` }} aria-hidden="true" />
                </li>
              ))}
            </ul>
          </Card>
        </div>
        <div className="column">
          <Card icon="layout" title="Radii">
            <ul className="gallery-radii">
              {RADII.map((r) => (
                <li key={r}>
                  <span className="gallery-radius" style={{ borderRadius: `var(--lm-radius-${r})` }} aria-hidden="true" />
                  <code>--lm-radius-{r}</code>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}

export function Typography() {
  return (
    <>
      <Lead>
        Sora for headings and the interface, the system monospace font for code. Arabic and Hebrew text falls back to the
        system font, because Sora has no glyphs for these scripts.
      </Lead>
      <Card icon="type" title="Headings">
        {[1, 2, 3, 4, 5, 6].map((n) => (
          <p key={n} className={`title is-${n}`}>
            Title {n}: Domains and certificates
          </p>
        ))}
        <p className="subtitle is-5">Subtitle: everything for example.org at a glance</p>
      </Card>
      <Card icon="type" title="Text">
        <div className="content">
          <p>
            Body text in the panel is set at 14px with a line height of 1.5. <strong>Strong text</strong>,{" "}
            <em>emphasis</em>, <a href="#typography">a link</a>, <code>inline code</code>, <kbd>Ctrl</kbd> + <kbd>K</kbd>{" "}
            and <small>small print</small>. German text keeps its umlauts and ß: Größenänderung, Übersicht, Domänen.
          </p>
          <ul>
            <li>Lists use the same spacing as paragraphs.</li>
            <li>
              Numbers are easy to compare: <span className="gallery-numbers">0123456789</span>
            </li>
          </ul>
          <blockquote>A short note, as the panel shows it in help texts.</blockquote>
          <pre>
            <code>{"python3 -m lumen_panel verify /home/keyhelp/www/keyhelp/theme/lumen"}</code>
          </pre>
          <p className="has-text-grey">Grey helper text, as used for hints and descriptions.</p>
          <p className="is-size-7 has-text-grey">Size 7 helper text, used in footers and table notes.</p>
        </div>
      </Card>
      <Card icon="type" title="Weights">
        <p className="gallery-weights">
          {[400, 500, 600, 700].map((w) => (
            <span key={w} style={{ fontWeight: w }}>
              Sora {w}
            </span>
          ))}
        </p>
      </Card>
    </>
  );
}

export function Shell({ onOpenUserMenu }: { onOpenUserMenu: () => void }) {
  return (
    <>
      <Lead>
        This gallery uses the same shell as the panel's internal pages: a fixed header, a sidebar with grouped links, the
        content area with breadcrumbs and a title, and a footer. The markup is written for this gallery; it carries the ids
        and classes the panel uses, so the Lumen stylesheet styles it exactly as it styles the panel.
      </Lead>
      <Card icon="layout" title="Regions">
        <div className="table-container">
          <table className="table is-fullwidth is-hoverable">
            <thead>
              <tr>
                <th scope="col">Region</th>
                <th scope="col">Selector</th>
                <th scope="col">What Lumen changes</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Header</th>
                <td>
                  <code>#header</code>, <code>#top-nav</code>
                </td>
                <td>surface colour, hairline border, Luminare logo, soft icon tiles, the command palette button</td>
              </tr>
              <tr>
                <th scope="row">User menu</th>
                <td>
                  <code>#user-menu</code>
                </td>
                <td>raised surface, rounded corner, one soft shadow</td>
              </tr>
              <tr>
                <th scope="row">Sidebar</th>
                <td>
                  <code>#sidebar-navigation</code>
                </td>
                <td>group labels in small caps, rounded items, a bar on the current page</td>
              </tr>
              <tr>
                <th scope="row">Content</th>
                <td>
                  <code>#content</code>
                </td>
                <td>page background, breadcrumbs, page title, 8px spacing grid</td>
              </tr>
              <tr>
                <th scope="row">Footer</th>
                <td>
                  <code>#footer</code>
                </td>
                <td>muted text with AA contrast</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
      <Card icon="user" title="User menu">
        <p className="has-margin-bottom-medium">
          The account link in the header opens the user menu, as in the panel. The command palette lists its links under
          "Account".
        </p>
        <button className="button is-link" type="button" onClick={onOpenUserMenu}>
          <Icon name="user" />
          <span>Open the user menu</span>
        </button>
      </Card>
      <Card icon="pages" title="Command palette">
        <p>
          Press <kbd>Ctrl</kbd> + <kbd>K</kbd> (<kbd>⌘</kbd> <kbd>K</kbd> on a Mac) or use the search button in the header.
          The palette reads this sidebar and the user menu, exactly as it reads the panel's own navigation, and renders in a
          shadow root, so neither its styles nor the page's can leak.
        </p>
      </Card>
    </>
  );
}
