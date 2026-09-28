// lib/contrast.js
//
// WCAG 2.1 contrast math over this app's own design tokens.
//
// This module exists because "it looks fine" is not a measurement. A sibling
// product (SlipScan) shipped tertiary text at 2.33:1 — comfortably illegible,
// and invisible to every reviewer who eyeballed it. The only thing that catches
// that class of defect is arithmetic, so the arithmetic lives here and
// `contrast.test.js` runs it against the REAL `src/index.css` on every
// `npm test`. Change a token to something unreadable and the suite goes red.
//
// Everything here is pure and DOM-free on purpose: it has to run under plain
// `node --test` with no browser, no jsdom and no build step.
//
// # Why alpha compositing is not optional
//
// Several tokens are deliberately translucent — the console chrome's
// `--sidebar-muted-foreground: 0 0% 100% / 0.6` is white at 60% over a near
// black sidebar. Measuring that as if it were opaque white reports 17.9:1 when
// the user's eye actually receives 8.7:1. A contrast checker that ignores alpha
// flatters exactly the tokens most likely to be too faint, so `composite()`
// runs before every ratio and the callers pass the surface each colour actually
// sits on.

export interface Hsl {
    h: number;
    s: number;
    l: number;
    a: number;
}

export interface Rgb {
    r: number;
    g: number;
    b: number;
    a?: number;
}

export interface Rgba extends Rgb {
    a: number;
}

/** Anything `toRgb`/`composite`/etc. accept: an HSL/hex token string, or an already-parsed colour. */
export type ColorInput = string | Rgb;

/**
 * parseHsl parses a CSS-custom-property HSL triple in the space-separated
 * form Tailwind/shadcn tokens use — `"38 91% 55%"` — with optional alpha
 * (`"0 0% 100% / 0.6"`). Returns `{ h, s, l, a }` with s/l as 0..1 fractions
 * and a defaulting to 1.
 *
 * Throws on anything it cannot parse rather than returning a silent black:
 * a token this can't read is a token nothing downstream can measure, and a
 * measurement gate that quietly scores unparseable input has stopped being a
 * gate.
 */
export function parseHsl(value: string): Hsl {
    const raw = String(value ?? '').trim();
    const m = raw.match(
        /^(-?[\d.]+)(?:deg)?\s+(-?[\d.]+)%\s+(-?[\d.]+)%(?:\s*\/\s*([\d.]+%?))?$/,
    );
    if (!m) throw new Error(`contrast: cannot parse HSL token ${JSON.stringify(raw)}`);

    const [, hs, ss, ls, as] = m;
    let a = 1;
    if (as !== undefined) {
        a = as.endsWith('%') ? Number(as.slice(0, -1)) / 100 : Number(as);
    }
    return { h: Number(hs), s: Number(ss) / 100, l: Number(ls) / 100, a };
}

/**
 * hslToRgb converts parsed HSL to 0..255 sRGB channels.
 */
export function hslToRgb({ h, s, l }: Pick<Hsl, 'h' | 's' | 'l'>): Rgb {
    const hue = ((h % 360) + 360) % 360;
    const c = (1 - Math.abs(2 * l - 1)) * s;
    const x = c * (1 - Math.abs(((hue / 60) % 2) - 1));
    const m = l - c / 2;

    let rgb: [number, number, number];
    if (hue < 60) rgb = [c, x, 0];
    else if (hue < 120) rgb = [x, c, 0];
    else if (hue < 180) rgb = [0, c, x];
    else if (hue < 240) rgb = [0, x, c];
    else if (hue < 300) rgb = [x, 0, c];
    else rgb = [c, 0, x];

    return {
        r: Math.round((rgb[0] + m) * 255),
        g: Math.round((rgb[1] + m) * 255),
        b: Math.round((rgb[2] + m) * 255),
    };
}

/**
 * hexToRgb parses `#rgb` / `#rrggbb`. Used for the handful of fixed brand
 * values that are not tokens (the logo tile, the ratified mini-site accent)
 * so they can be measured against the same yardstick as everything else.
 */
export function hexToRgb(hex: string): Rgb {
    const s = String(hex ?? '').trim().replace(/^#/, '');
    const full = s.length === 3 ? s.split('').map((ch) => ch + ch).join('') : s;
    if (!/^[0-9a-fA-F]{6}$/.test(full)) {
        throw new Error(`contrast: cannot parse hex colour ${JSON.stringify(hex)}`);
    }
    return {
        r: parseInt(full.slice(0, 2), 16),
        g: parseInt(full.slice(2, 4), 16),
        b: parseInt(full.slice(4, 6), 16),
    };
}

/**
 * toRgb accepts either an HSL token string, a hex string, or an already
 * parsed `{r,g,b}` and normalises to `{r,g,b,a}`.
 */
export function toRgb(value: ColorInput): Rgba {
    if (value && typeof value === 'object' && 'r' in value) {
        return { r: value.r, g: value.g, b: value.b, a: value.a ?? 1 };
    }
    const s = String(value ?? '').trim();
    if (s.startsWith('#')) return { ...hexToRgb(s), a: 1 };
    const hsl = parseHsl(s);
    return { ...hslToRgb(hsl), a: hsl.a };
}

/**
 * composite flattens a possibly-translucent foreground over an opaque
 * backdrop using standard source-over alpha blending, returning the colour
 * the eye actually receives.
 *
 * This is the step that makes a translucent token measurable. `--sidebar-
 * muted-foreground` is `0 0% 100% / 0.6`; measured raw it scores as pure
 * white, which is a number no user ever sees.
 *
 * @param {string|object} fg foreground, may carry alpha
 * @param {string|object} bg backdrop; its own alpha is ignored (it is the
 *   bottom of the stack by definition)
 * @returns {{r: number, g: number, b: number, a: 1}}
 */
export function composite(fg: ColorInput, bg: ColorInput): Rgba {
    const f = toRgb(fg);
    const b = toRgb(bg);
    const a = f.a;
    return {
        r: Math.round(f.r * a + b.r * (1 - a)),
        g: Math.round(f.g * a + b.g * (1 - a)),
        b: Math.round(f.b * a + b.b * (1 - a)),
        a: 1,
    };
}

/**
 * relativeLuminance implements WCAG 2.1's definition (sRGB channels
 * linearised, then weighted 0.2126/0.7152/0.0722). Input must be opaque —
 * composite() first if it is not.
 *
 * @param {string|object} color
 * @returns {number} 0..1
 */
export function relativeLuminance(color: ColorInput): number {
    const { r, g, b } = toRgb(color);
    const linearize = (channel: number) => {
        const c = channel / 255;
        return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b);
}

/**
 * contrastRatio returns the WCAG 2.1 ratio between two colours, 1..21.
 *
 * A translucent `fg` is composited over `bg` first, so callers pass tokens
 * as-written and still get the number a human eye receives. `bg` is treated
 * as opaque; where a surface is itself translucent (the sidebar's
 * `--sidebar-accent`), composite it against its own backdrop and pass the
 * result.
 *
 * @param {string|object} fg
 * @param {string|object} bg
 * @returns {number}
 */
export function contrastRatio(fg: ColorInput, bg: ColorInput): number {
    const backdrop = toRgb(bg);
    const front = composite(fg, backdrop);
    const l1 = relativeLuminance(front);
    const l2 = relativeLuminance(backdrop);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
}

/**
 * round2 is the reporting precision used everywhere contrast is printed or
 * asserted. Truncates toward zero rather than rounding to nearest, so a
 * measured 4.499 reports as 4.49 and never as a passing-looking "4.5".
 *
 * @param {number} n
 * @returns {number}
 */
export function round2(n: number): number {
    return Math.floor(n * 100) / 100;
}

/** WCAG 2.1 AA thresholds, by the role the text plays. */
export const AA_NORMAL_TEXT = 4.5;
/** Text >= 18.66px bold or >= 24px regular. */
export const AA_LARGE_TEXT = 3;
/** Non-text: UI component boundaries, focus indicators, icon glyphs (1.4.11). */
export const AA_NON_TEXT = 3;

/**
 * meets reports whether a measured ratio clears a threshold, comparing at
 * the same 2dp precision the report prints. Without this a pair measuring
 * 4.4999 would be asserted against its full-precision value while the report
 * printed "4.49", and the gate and the evidence would disagree.
 *
 * @param {number} ratio
 * @param {number} threshold
 * @returns {boolean}
 */
export function meets(ratio: number, threshold: number): boolean {
    return round2(ratio) >= threshold;
}
