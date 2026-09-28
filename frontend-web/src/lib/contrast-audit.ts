// lib/contrast-audit.js
//
// The list of colour pairs this app promises are legible, and the thresholds
// they are held to.
//
// It lives in one file so the TEST and the REPORT cannot disagree.
// `contrast.test.js` fails the build on any pair below its threshold;
// `scripts/contrast-report.mjs` prints the same rows as a table. A palette
// change that breaks a pair therefore turns the suite red AND shows up in the
// report with the number that broke it — there is no path where the evidence
// and the gate tell different stories.
//
// # What is audited, and why those things
//
// Every pair below is one a user actually looks at: a foreground token over
// the specific surface it is rendered on. Pairs are named for the situation,
// not the tokens, because "muted-foreground on card" is the thing that goes
// wrong, and `text-muted-foreground` inside a `<Card>` is where it goes wrong.
//
// Translucent tokens are composited over their real backdrop before scoring
// (lib/contrast.js) — the console chrome's tokens are white at 10–60% alpha
// and measuring them raw would report the contrast of pure white, which is
// not a number anybody's eye receives.

import { contrastRatio, AA_NORMAL_TEXT, AA_LARGE_TEXT, AA_NON_TEXT, composite, type ColorInput } from './contrast.ts';
import { token } from './theme-tokens.ts';

export { AA_NORMAL_TEXT, AA_LARGE_TEXT, AA_NON_TEXT };

/** One audited token pair — a foreground rendered on a background, held to a WCAG threshold. */
export interface Pair {
    name: string;
    fg: string;
    bg: string;
    /** Opaque surface a translucent `bg` sits on, flattened before use as a backdrop. */
    over?: string;
    threshold: number;
}

/** One measured pair, ready to report or assert against. */
export interface Measurement {
    name: string;
    ratio: number;
    threshold: number;
    pass: boolean;
    fg: string;
    bg: string;
}

/**
 * PAIRS describes every audited combination.
 *
 * `fg`/`bg` name tokens. `over` (optional) names the opaque surface a
 * translucent `bg` sits on, so the backdrop is flattened before it is used as
 * a backdrop — without it, a 16%-alpha wash would be scored as if it were a
 * solid colour it never is.
 *
 * `threshold` is the WCAG 2.1 AA bar for the ROLE the colour plays:
 *   - AA_NORMAL_TEXT (4.5) — body copy, labels, anything under ~18px.
 *   - AA_LARGE_TEXT (3) — only where the type is genuinely large and bold.
 *   - AA_NON_TEXT (3) — 1.4.11: focus indicators and control boundaries.
 */
export const PAIRS: Pair[] = [
    // ── Body and surfaces ────────────────────────────────────────────────
    { name: 'body text on page', fg: 'foreground', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'card text on card', fg: 'card-foreground', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'popover text on popover', fg: 'popover-foreground', bg: 'popover', threshold: AA_NORMAL_TEXT },

    // The SlipScan failure mode: secondary/tertiary prose is where contrast
    // quietly dies, and it is measured against all three surfaces it lands
    // on rather than only the page.
    { name: 'muted text on page', fg: 'muted-foreground', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'muted text on card', fg: 'muted-foreground', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'muted text on muted fill', fg: 'muted-foreground', bg: 'muted', threshold: AA_NORMAL_TEXT },
    { name: 'secondary text on secondary fill', fg: 'secondary-foreground', bg: 'secondary', threshold: AA_NORMAL_TEXT },

    // ── Brand ────────────────────────────────────────────────────────────
    // The pair that justifies --primary-emphasis existing. `text-primary` on
    // a light page is 1.99:1, so brand-coloured INK is a different token and
    // it is measured here on both surfaces it appears on.
    { name: 'brand ink on page', fg: 'primary-emphasis', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'brand ink on card', fg: 'primary-emphasis', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'label on primary button', fg: 'primary-foreground', bg: 'primary', threshold: AA_NORMAL_TEXT },
    { name: 'accent text on accent fill', fg: 'accent-foreground', bg: 'accent', threshold: AA_NORMAL_TEXT },

    // ── Status, as text and as fill ──────────────────────────────────────
    { name: 'success text on page', fg: 'success', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'success text on card', fg: 'success', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'label on success fill', fg: 'success-foreground', bg: 'success', threshold: AA_NORMAL_TEXT },
    { name: 'destructive text on page', fg: 'destructive', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'destructive text on card', fg: 'destructive', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'label on destructive fill', fg: 'destructive-foreground', bg: 'destructive', threshold: AA_NORMAL_TEXT },
    { name: 'warning text on page', fg: 'warning', bg: 'background', threshold: AA_NORMAL_TEXT },
    { name: 'warning text on card', fg: 'warning', bg: 'card', threshold: AA_NORMAL_TEXT },
    { name: 'label on warning fill', fg: 'warning-foreground', bg: 'warning', threshold: AA_NORMAL_TEXT },

    // ── Gate verdicts ────────────────────────────────────────────────────
    // The most important rows in this table. These are read outdoors, at
    // speed, by somebody who cannot ask the server what happened.
    { name: 'ADMIT flood text', fg: 'verdict-ink', bg: 'verdict-admit', threshold: AA_NORMAL_TEXT },
    { name: 'REJECT flood text', fg: 'verdict-ink', bg: 'verdict-reject', threshold: AA_NORMAL_TEXT },
    { name: 'ALREADY SCANNED flood text', fg: 'verdict-ink', bg: 'verdict-duplicate', threshold: AA_NORMAL_TEXT },

    // ── Console chrome (translucent; composited before scoring) ──────────
    { name: 'sidebar label', fg: 'sidebar-foreground', bg: 'sidebar-background', threshold: AA_NORMAL_TEXT },
    { name: 'sidebar muted label', fg: 'sidebar-muted-foreground', bg: 'sidebar-background', threshold: AA_NORMAL_TEXT },
    {
        name: 'sidebar hovered item label',
        fg: 'sidebar-accent-foreground',
        bg: 'sidebar-accent',
        over: 'sidebar-background',
        threshold: AA_NORMAL_TEXT,
    },
    {
        name: 'sidebar active item label',
        fg: 'sidebar-primary-foreground',
        bg: 'sidebar-primary',
        over: 'sidebar-background',
        threshold: AA_NORMAL_TEXT,
    },

    // ── Non-text (WCAG 1.4.11) ───────────────────────────────────────────
    // The focus ring has to be visible against everything it can surround.
    { name: 'focus ring on page', fg: 'ring', bg: 'background', threshold: AA_NON_TEXT },
    { name: 'focus ring on card', fg: 'ring', bg: 'card', threshold: AA_NON_TEXT },
    { name: 'focus ring on muted fill', fg: 'ring', bg: 'muted', threshold: AA_NON_TEXT },
    // A text field is identified by its border. `--input` was a 1.3:1
    // hairline before this pass — decorative, and invisible as an affordance.
    { name: 'input border on page', fg: 'input', bg: 'background', threshold: AA_NON_TEXT },
    { name: 'input border on card', fg: 'input', bg: 'card', threshold: AA_NON_TEXT },
];

/**
 * GATE_PAIRS audits the scan screen's fixed surface. It is deliberately NOT
 * theme-derived: `.gate-surface` pins its own near-black canvas in both
 * themes (a light flood behind a camera preview is glare outdoors), so its
 * colours are literals here and are measured once rather than twice.
 *
 * The verdict rows use AA_NON_TEXT because what is being asserted is that a
 * flood is distinguishable FROM THE CHROME it replaces — that a glance at the
 * screen tells you something happened. The legibility of the words inside the
 * flood is asserted separately in PAIRS.
 */
export const GATE_SURFACE = {
    bg: '0 0% 0%',
    ink: '0 0% 100%',
    inkMuted: '0 0% 78%',
};

export const GATE_PAIRS: Pair[] = [
    { name: 'gate chrome text', fg: GATE_SURFACE.ink, bg: GATE_SURFACE.bg, threshold: AA_NORMAL_TEXT },
    { name: 'gate chrome muted text', fg: GATE_SURFACE.inkMuted, bg: GATE_SURFACE.bg, threshold: AA_NORMAL_TEXT },
    { name: 'ADMIT flood vs gate chrome', fg: '150 70% 29%', bg: GATE_SURFACE.bg, threshold: AA_NON_TEXT },
    { name: 'REJECT flood vs gate chrome', fg: '0 78% 46%', bg: GATE_SURFACE.bg, threshold: AA_NON_TEXT },
    { name: 'ALREADY SCANNED flood vs gate chrome', fg: '28 95% 34%', bg: GATE_SURFACE.bg, threshold: AA_NON_TEXT },
];

// The verdict literals above are duplicated from index.css, which is exactly
// the drift this module otherwise exists to prevent — so verdictTokensMatch()
// below is asserted by contrast.test.js against the parsed stylesheet. If the
// two ever disagree the suite fails and names the token, rather than the gate
// quietly measuring a colour the app stopped using.

/**
 * verdictTokensMatch compares the GATE_PAIRS literals against the real
 * `--verdict-*` tokens, returning the mismatches.
 *
 * @param scope a theme token map
 */
export function verdictTokensMatch(scope: Record<string, string>): Array<{ token: string; inCss: string; inAudit: string }> {
    const expected: Record<string, string> = {
        '--verdict-admit': '150 70% 29%',
        '--verdict-reject': '0 78% 46%',
        '--verdict-duplicate': '28 95% 34%',
    };
    const mismatches: Array<{ token: string; inCss: string; inAudit: string }> = [];
    for (const [name, inAudit] of Object.entries(expected)) {
        const inCss = token(scope, name);
        if (inCss !== inAudit) mismatches.push({ token: name, inCss, inAudit });
    }
    return mismatches;
}

/**
 * measurePair resolves a pair's tokens against a theme scope and returns the
 * measured ratio plus whether it clears its threshold.
 *
 * @param scope light or dark token map
 */
export function measurePair(scope: Record<string, string>, pair: Pair): Measurement {
    const fg = token(scope, pair.fg);
    let bg: ColorInput = token(scope, pair.bg);
    if (pair.over) {
        // Flatten a translucent surface onto the opaque one beneath it, so
        // the backdrop used for scoring is the colour that is actually there.
        bg = composite(bg, token(scope, pair.over));
    }
    const ratio = contrastRatio(fg, bg);
    return {
        name: pair.name,
        ratio,
        threshold: pair.threshold,
        pass: Math.floor(ratio * 100) / 100 >= pair.threshold,
        fg: pair.fg,
        bg: pair.bg,
    };
}

/**
 * measureLiteralPair is measurePair for the gate surface, whose colours are
 * literals rather than tokens.
 */
export function measureLiteralPair(pair: Pair): Measurement {
    const ratio = contrastRatio(pair.fg, pair.bg);
    return {
        name: pair.name,
        ratio,
        threshold: pair.threshold,
        pass: Math.floor(ratio * 100) / 100 >= pair.threshold,
        fg: pair.fg,
        bg: pair.bg,
    };
}

/**
 * auditTheme measures every PAIRS row against one theme scope.
 */
export function auditTheme(scope: Record<string, string>): Measurement[] {
    return PAIRS.map((pair) => measurePair(scope, pair));
}
