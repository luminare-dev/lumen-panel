// Read design tokens as the browser resolves them and compute WCAG 2.x contrast ratios.
// The colours are normalised through a probe element, so any CSS colour syntax works (the
// minified stylesheet may write #fff or rgb()).

export type Rgb = [number, number, number];

let probe: HTMLElement | null = null;

export function toRgb(value: string): Rgb | null {
  if (!value) return null;
  if (!probe) {
    probe = document.createElement("span");
    probe.setAttribute("aria-hidden", "true");
    probe.style.display = "none";
    document.body.appendChild(probe);
  }
  probe.style.color = "";
  probe.style.color = value;
  if (!probe.style.color) return null;
  const m = getComputedStyle(probe).color.match(/rgba?\(\s*(\d+(?:\.\d+)?)[,\s]+(\d+(?:\.\d+)?)[,\s]+(\d+(?:\.\d+)?)(?:\s*[,/]\s*([\d.]+%?))?\s*\)/u);
  if (!m) return null;
  if (m[4] !== undefined && m[4] !== "1" && m[4] !== "100%") return null; // translucent: no single ratio
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

export function hex([r, g, b]: Rgb): string {
  return `#${[r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("").toUpperCase()}`;
}

function channel(c: number): number {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
}

export function luminance([r, g, b]: Rgb): number {
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

export function ratio(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

/** Rounded down to two decimals, so a shown 4.50 never hides a real 4.497. */
export function formatRatio(r: number): string {
  return `${(Math.floor(r * 100) / 100).toFixed(2)}:1`;
}

export function readToken(name: string, from: Element = document.body): Rgb | null {
  return toRgb(getComputedStyle(from).getPropertyValue(`--lm-${name}`).trim());
}
