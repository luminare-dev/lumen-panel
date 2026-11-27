// Lumen tokens for KeyHelp: the override stylesheet a token file compiles to.
//
// core.ts is a byte-for-byte copy of the Hydrodactyl theme's compiler (shared.lock). This file adds
// what the KeyHelp theme needs on top: the selectors KeyHelp's dark mode uses, the mapping from the
// 16 colour roles to the theme's own --lm-* variables, a few layout rules and the URLs of the
// files a customization ships. The customizer page runs the same code (customizer/build.mjs
// embeds it), so a ZIP made there and `node tokens/compile.mjs` print the same bytes.

import { type ColorKey, compile, kebab, sanitizeCustomCss, type ThemeMode, type Tokens } from './core.ts';

/**
 * `follow`: light on :root, dark where KeyHelp renders a page in dark mode (Lumen's lumen.css and
 * lumen-rtl.css). `dark`: always dark (Lumen's -dark stylesheets and every Lumen Dark stylesheet).
 */
export type Kind = 'follow' | 'dark';

/** Which override goes after which stylesheet of the theme. */
export const STYLESHEET_KINDS: Record<string, Kind> = {
    'lumen.css': 'follow',
    'lumen-rtl.css': 'follow',
    'lumen-dark.css': 'dark',
    'lumen-dark-rtl.css': 'dark',
    'lumen-night.css': 'dark',
    'lumen-night-rtl.css': 'dark',
};

const LIGHT = ':root';
const DARK_FOLLOW = ':root:has(> body.dark-mode),\nbody.dark-mode';
const DARK_ALWAYS = ':root,\n:root:has(> body.dark-mode),\nbody.dark-mode';

/**
 * Token URLs are portable between Lumen themes. The override is appended to a stylesheet in
 * theme/<variant>/assets/, so relative URLs work for both variants: shipped logos are in brand/,
 * the files of a customization in custom/.
 */
export const URL_PREFIXES: [string, string][] = [
    ['/lumen/brand/', 'brand/'],
    ['/storage/lumen/', 'custom/'],
];

export function resolveUrl(value: string): string {
    for (const [from, to] of URL_PREFIXES) {
        if (value.startsWith(from)) return to + value.slice(from.length);
    }
    return value;
}

export function resolveCssUrls(css: string): string {
    let out = css;
    for (const [from, to] of URL_PREFIXES) out = out.split(`url("${from}`).join(`url("${to}`);
    return out;
}

function v(key: ColorKey): string {
    return `var(--lumen-${kebab(key)})`;
}

function mix(a: string, b: string, percentOfA: string): string {
    return `color-mix(in srgb, ${a} ${percentOfA}%, ${b})`;
}

/** The theme's --lm-* colour variables as mixes of the roles of one mode. */
export function roleLines(tokens: Tokens, mode: ThemeMode): string[] {
    const dark = mode === 'dark';
    const lines = [
        `color-scheme: ${mode};`,
        `--lm-bg: ${v('canvas')};`,
        `--lm-surface: ${v('surface')};`,
        `--lm-surface-raised: ${mix(v('surfaceRaised'), v('surface'), '50')};`,
        `--lm-surface-sunken: ${v('surfaceSunken')};`,
        `--lm-surface-hover: ${v('surfaceRaised')};`,
        `--lm-border: ${v('border')};`,
        `--lm-border-control: ${mix(v('textMuted'), v('border'), '70')};`,
        `--lm-text: ${v('text')};`,
        `--lm-text-strong: ${v('text')};`,
        `--lm-text-2: ${mix(v('text'), v('textMuted'), '45')};`,
        `--lm-text-muted: ${v('textMuted')};`,
        `--lm-link: ${v('accentText')};`,
        `--lm-link-hover: ${mix(v('accentText'), v('text'), '75')};`,
        `--lm-primary: ${v('accent')};`,
        `--lm-primary-hover: ${mix(v('accent'), v('accentSecondary'), '60')};`,
        `--lm-primary-active: ${v('accentSecondary')};`,
        `--lm-on-primary: ${v('accentContrast')};`,
        `--lm-primary-tint: ${mix(v('accent'), v('surface'), dark ? '14' : '10')};`,
        `--lm-on-primary-tint: ${v('accentText')};`,
        `--lm-focus: ${v('focus')};`,
    ];
    for (const status of ['success', 'warning', 'danger', 'info'] as const) {
        lines.push(
            `--lm-${status}: ${v(status)};`,
            `--lm-on-${status}: ${v('surface')};`,
            `--lm-${status}-tint: ${mix(v(status), v('surface'), dark ? '14' : '10')};`,
            `--lm-${status}-text: ${mix(v(status), v('text'), '80')};`,
        );
    }
    lines.push(
        `--lm-overlay: ${mix(dark ? v('canvas') : v('text'), 'transparent', dark ? '72' : '55')};`,
        `--lm-shadow-1: var(--shadow-xs);`,
        `--lm-shadow-2: var(--shadow-lg);`,
        `--lm-glow-1: ${tokens.layout.backgroundGlow ? 'var(--lumen-glow)' : 'transparent'};`,
        `--lm-glow-2: ${tokens.layout.backgroundGlow ? 'var(--lumen-glow-secondary)' : 'transparent'};`,
    );
    return lines;
}

/** Fonts, shape and spacing: the theme's --lm-* units from the shared values. */
export function sharedLines(tokens: Tokens): string[] {
    const space: [string, string][] = [
        ['1', '1'],
        ['2', '2'],
        ['3', '3'],
        ['4', '4'],
        ['5', '6'],
        ['6', '8'],
        ['7', '12'],
    ];
    // The theme's radii at the default 14px card radius: 6, 10, 12 and 14px.
    const radius: [string, string][] = [
        ['s', '0.43'],
        ['m', '0.71'],
        ['l', '0.86'],
        ['xl', '1'],
    ];
    const lines = [`--lm-font: var(--lumen-font-body);`, `--lm-font-mono: var(--lumen-font-mono);`];
    for (const [step, factor] of space) lines.push(`--lm-space-${step}: calc(var(--spacing) * ${factor});`);
    for (const [step, factor] of radius) lines.push(`--lm-radius-${step}: calc(var(--lumen-radius) * ${factor});`);
    return lines;
}

/** Rules for the switches that are not plain values. */
export function ruleBlocks(tokens: Tokens): string[] {
    const rules: string[] = [
        'html {\n    font-size: calc(14px * var(--lumen-font-scale));\n}\n',
        'h1, h2, h3, h4, .title, .subtitle, .card-header-title, .modal-card-title {\n' +
            '    font-family: var(--lumen-font-display);\n' +
            '    font-weight: var(--lumen-heading-weight);\n}\n',
    ];
    if (!tokens.elevation.borders) {
        rules.push('.card, .box, .modal-card, .dropdown-content {\n    border-color: transparent;\n}\n');
    }
    if (tokens.layout.indicator === 'bar') {
        rules.push(
            '#sidebar .menu-list a.is-active {\n    background-color: transparent;\n    color: var(--lm-primary);\n}\n',
        );
    } else if (tokens.layout.indicator === 'glow') {
        rules.push(
            '#sidebar .menu-list a.is-active {\n' +
                '    box-shadow: 0 0 0 1px color-mix(in srgb, var(--lm-primary) 35%, transparent), 0 0 18px -4px var(--lm-primary);\n}\n' +
                '#sidebar .menu-list a.is-active::before {\n    display: none;\n}\n',
        );
    }
    if (tokens.branding.loginBackground !== '') {
        rules.push(
            '.hero.is-primary.lumen-extern {\n' +
                '    background-image: linear-gradient(color-mix(in srgb, var(--lm-bg) 55%, transparent), color-mix(in srgb, var(--lm-bg) 55%, transparent)), var(--lumen-login-background);\n' +
                '    background-position: center;\n    background-size: cover;\n}\n',
        );
    }
    return rules;
}

const ROOT = ':root';

/** The override for one kind of stylesheet: shared values, the roles of each mode, the rules. */
export function compileKeyHelp(tokens: Tokens, kind: Kind): string {
    const block = (selector: string, lines: string[]) => `${selector} {\n    ${lines.join('\n    ')}\n}\n`;
    const core = compile(tokens, { scope: ROOT, withCustomCss: false });
    const darkHead = `${ROOT}[data-theme="dark"] {`;
    const lightHead = `${ROOT}[data-theme="light"] {`;
    const lightAt = core.indexOf(lightHead);
    const darkAt = core.indexOf(darkHead);
    const shared = core.slice(0, darkAt);
    const darkRoles = core.slice(darkAt + darkHead.length, lightAt);
    const lightRoles = core.slice(lightAt + lightHead.length);

    let css = shared + block(ROOT, sharedLines(tokens));
    if (kind === 'follow') {
        css += LIGHT + ' {' + lightRoles + block(LIGHT, roleLines(tokens, 'light'));
        css += DARK_FOLLOW + ' {' + darkRoles + block(DARK_FOLLOW, roleLines(tokens, 'dark'));
    } else {
        css += DARK_ALWAYS + ' {' + darkRoles + block(DARK_ALWAYS, roleLines(tokens, 'dark'));
    }
    css += ruleBlocks(tokens).join('');
    if (tokens.customCss.trim() !== '') css += `/* custom CSS */\n${sanitizeCustomCss(tokens.customCss)}\n`;
    return resolveCssUrls(css);
}

/** The shipped Luminare marks stand for the theme's Luminare lockups in the header and login. */
export const LUMINARE_LOCKUPS: Record<string, { header: string; login: string }> = {
    'brand/luminare-mark.svg': {
        header: 'brand/luminare-lockup-compact-dark.svg',
        login: 'brand/luminare-lockup-horizontal-dark.svg',
    },
    'brand/luminare-mark-brand-deep.svg': {
        header: 'brand/luminare-lockup-compact-light.svg',
        login: 'brand/luminare-lockup-horizontal-light.svg',
    },
};

/**
 * What the template patches show (branding.json of a customization). Each logo is a path below
 * theme/<variant>/assets/ (brand/… or custom/…), an https URL, or '' for KeyHelp's own logo.
 */
export interface Branding {
    headerLight: string;
    headerDark: string;
    loginLight: string;
    loginDark: string;
    favicon: string;
    productName: string;
}

export function branding(tokens: Tokens): Branding {
    const b = tokens.branding;
    const light = resolveUrl(b.logoLight !== '' ? b.logoLight : b.logoDark);
    const dark = resolveUrl(b.logoDark !== '' ? b.logoDark : b.logoLight);
    const pick = (logo: string, place: 'header' | 'login') => LUMINARE_LOCKUPS[logo]?.[place] ?? logo;
    return {
        headerLight: pick(light, 'header'),
        headerDark: pick(dark, 'header'),
        loginLight: pick(light, 'login'),
        loginDark: pick(dark, 'login'),
        favicon: resolveUrl(b.favicon),
        productName: b.productName,
    };
}

/** Text of branding.json (two-space JSON, keys in a fixed order). */
export function brandingJson(tokens: Tokens): string {
    return `${JSON.stringify(branding(tokens), null, 2)}\n`;
}

/** README.txt of a customization. */
export function readme(tokens: Tokens): string {
    return (
        `Lumen customization for lumen-panel: ${tokens.meta.name.replace(/[^\x20-\x7e]/g, '')}\n\n` +
        'Install on the panel server (a dry run; add --yes to install):\n' +
        '  cd /opt/lumen-panel/generator\n' +
        '  python3 -m lumen_panel apply-custom <this ZIP> --keyhelp /home/keyhelp/www/keyhelp\n\n' +
        'Contents: lumen.tokens.json (the token file; import it or this ZIP in the customizer to edit it\n' +
        'again), override-follow.css and override-dark.css (compiled from the tokens), branding.json and\n' +
        'the uploaded files in custom/. No KeyHelp file is included.\n' +
        'https://github.com/luminare-dev/lumen-panel\n'
    );
}

/** The text files of a customization (uploads go into custom/ beside them), keyed by path. */
export function customizationFiles(tokens: Tokens): Record<string, string> {
    return {
        'lumen.tokens.json': `${JSON.stringify(tokens, null, 2)}\n`,
        'override-follow.css': compileKeyHelp(tokens, 'follow'),
        'override-dark.css': compileKeyHelp(tokens, 'dark'),
        'branding.json': brandingJson(tokens),
        'README.txt': readme(tokens),
    };
}
