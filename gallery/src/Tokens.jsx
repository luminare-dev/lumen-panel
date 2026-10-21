// Design tokens as the browser resolves them right now (light or dark), with live contrast
// ratios for the main pairs. The full table for both modes is docs/contrast.md.
import { useEffect, useState } from "react";

const SWATCHES = [
  "bg", "surface", "surface-raised", "surface-sunken", "surface-hover", "border", "border-control",
  "text", "text-2", "text-muted", "link", "primary", "primary-tint", "focus",
  "success", "warning", "danger", "info",
];

const PAIRS = [
  ["text", "surface", 4.5],
  ["text-2", "surface", 4.5],
  ["text-muted", "surface", 4.5],
  ["link", "surface", 4.5],
  ["on-primary", "primary", 4.5],
  ["on-primary-tint", "primary-tint", 4.5],
  ["danger-text", "danger-tint", 4.5],
  ["border-control", "surface", 3],
  ["focus", "surface", 3],
];

function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const lin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

function ratio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function readTokens() {
  const style = getComputedStyle(document.body);
  const names = new Set([...SWATCHES, ...PAIRS.flatMap(([a, b]) => [a, b])]);
  const values = {};
  for (const name of names) values[name] = style.getPropertyValue(`--lm-${name}`).trim().toUpperCase();
  return values;
}

export function Tokens({ mode }) {
  const [values, setValues] = useState({});
  useEffect(() => {
    // Read after the stylesheet for the new mode has applied.
    const id = window.setTimeout(() => setValues(readTokens()), 150);
    return () => window.clearTimeout(id);
  }, [mode]);
  const isHex = (v) => /^#[0-9A-F]{6}$/u.test(v || "");
  return (
    <section id="tokens" aria-labelledby="tokens-title">
      <h2 className="title is-5" id="tokens-title">Design tokens ({mode} mode)</h2>
      <div className="card has-margin-bottom-large">
        <div className="card-content">
          <ul className="gallery-swatches">
            {SWATCHES.map((name) => (
              <li key={name}>
                <span className="gallery-swatch" style={{ background: `var(--lm-${name})` }} aria-hidden="true" />
                <code>--lm-{name}</code>
                <span className="has-text-grey">{values[name] || "…"}</span>
              </li>
            ))}
          </ul>
          <div className="table-container has-margin-top-large">
            <table className="table is-fullwidth is-striped">
              <caption className="has-text-left has-text-grey">Contrast of the main pairs, computed in this browser</caption>
              <thead>
                <tr>
                  <th>Foreground</th>
                  <th>Background</th>
                  <th className="has-text-right">Ratio</th>
                  <th className="has-text-right">Needed</th>
                </tr>
              </thead>
              <tbody>
                {PAIRS.map(([fg, bg, min]) => {
                  const ok = isHex(values[fg]) && isHex(values[bg]);
                  const r = ok ? ratio(values[fg], values[bg]) : null;
                  return (
                    <tr key={`${fg}-${bg}`}>
                      <td>
                        <code>--lm-{fg}</code>
                      </td>
                      <td>
                        <code>--lm-{bg}</code>
                      </td>
                      <td className="has-text-right">
                        {r === null ? "…" : `${(Math.floor(r * 100) / 100).toFixed(2)}:1`}{" "}
                        {r !== null && <span className={`tag ${r >= min ? "is-success" : "is-danger"}`}>{r >= min ? "pass" : "fail"}</span>}
                      </td>
                      <td className="has-text-right">{min}:1</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  );
}
