// Accessibility gate: every audited colour pair, measured against the real
// stylesheet, in both themes.
//
// This is the test SlipScan did not have. Its audit found tertiary text at
// 2.33:1 — a defect no amount of looking catches and one line of arithmetic
// does. So the arithmetic runs on every `npm test`, over `src/index.css`
// itself rather than a copy of the palette, and a token nudged into
// illegibility fails the build with the measured number attached.
//
// Structured so a failure is immediately actionable: one subtest per theme
// per pair, named for the situation a user is in, reporting the ratio it got
// and the one it needed.
//
// # The rule this file exists to enforce
//
// When a pair fails, the COLOUR changes. The threshold never does. Relaxing a
// threshold to make a red build green does not make anything legible; it only
// moves the defect somewhere nobody is measuring. Every threshold below is a
// WCAG 2.1 AA figure for the role the colour plays, and none of them is a
// judgement call this repo gets to make.
//
// # Counting
//
// `measurements taken` at the bottom asserts the exact number of ratios this
// file computed. A test that quietly stops examining anything — an emptied
// table, a `for` loop over a renamed export — still passes every assertion it
// makes, because it makes none. The count is what catches that.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

import {
    parseHsl,
    hexToRgb,
    composite,
    contrastRatio,
    relativeLuminance,
    round2,
    meets,
    AA_NORMAL_TEXT,
    AA_LARGE_TEXT,
    AA_NON_TEXT,
    type ColorInput,
} from './contrast.ts';
import { readThemeTokens, token } from './theme-tokens.ts';
import { PAIRS, GATE_PAIRS, measurePair, measureLiteralPair, verdictTokensMatch } from './contrast-audit.ts';

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, '..', 'index.css'), 'utf8');
const themes = readThemeTokens(css);

/** Every ratio this file computes bumps this. Asserted at the end. */
let measurements = 0;
function ratio(fg: ColorInput, bg: ColorInput) {
    measurements++;
    return contrastRatio(fg, bg);
}

// ── The palette, as the design spec states it ───────────────────────────────
// The three brand colours and their derived tints, written as the hex the
// spec names them by. Nothing below trusts these to be reachable from the
// stylesheet — the tests assert that the TOKENS resolve to them.

const BLUE = '#155DFC'; // Tdev primary / fest blue
const WHITE = '#FFFFFF';
const BLACK = '#000000'; // Tdev dominant ground

// ── The maths itself ────────────────────────────────────────────────────────
// A contrast gate is only worth its assertions if its arithmetic is right, so
// the arithmetic is pinned against values that can be checked by hand.

test('contrast maths', async (t) => {
    await t.test('black on white is 21:1 and white on black is the same', () => {
        assert.equal(round2(ratio('0 0% 0%', '0 0% 100%')), 21);
        assert.equal(round2(ratio('0 0% 100%', '0 0% 0%')), 21);
    });

    await t.test('a colour against itself is 1:1', () => {
        assert.equal(round2(ratio('0 100% 64.1%', '0 100% 64.1%')), 1);
    });

    await t.test('relative luminance matches WCAG reference points', () => {
        assert.equal(round2(relativeLuminance('0 0% 100%')), 1);
        assert.equal(relativeLuminance('0 0% 0%'), 0);
    });

    await t.test('parses HSL tokens with and without alpha', () => {
        assert.deepEqual(parseHsl('0 0% 50%'), { h: 0, s: 0, l: 0.5, a: 1 });
        assert.deepEqual(parseHsl('0 0% 100% / 0.6'), { h: 0, s: 0, l: 1, a: 0.6 });
        // The brand's own fractional lightness, which is where a naive
        // `/100` would introduce float noise.
        const brand = parseHsl('0 100% 64.1%');
        assert.equal(brand.h, 0);
        assert.equal(brand.s, 1);
        assert.ok(Math.abs(brand.l - 0.641) < 1e-9, `l=${brand.l}`);
    });

    await t.test('refuses to score an unparseable token rather than defaulting it', () => {
        // A gate that silently scores garbage as black has stopped being a gate.
        assert.throws(() => parseHsl('rebeccapurple'), /cannot parse HSL/);
        assert.throws(() => hexToRgb('#12345'), /cannot parse hex/);
        assert.throws(() => token(themes.light, '--no-such-token'), /is not defined/);
    });

    await t.test('compositing alpha changes the answer (and is therefore not optional)', () => {
        // --sidebar-muted-foreground is white at 60% over the near-black
        // sidebar. Scored raw it looks like pure white; scored honestly it is
        // a full 10 points of ratio lower.
        const sidebar = token(themes.light, '--sidebar-background');
        const raw = ratio('0 0% 100%', sidebar);
        const composited = ratio('0 0% 100% / 0.6', sidebar);
        assert.ok(raw > 17, `opaque white measured ${round2(raw)}`);
        assert.ok(composited < 8, `60% white measured ${round2(composited)}`);
    });
});

// ── The tokens really are the brand colours ─────────────────────────────────

test('the shipped tokens are the brand colours the spec names', async (t) => {
    /**
     * assertIsHex checks an HSL token round-trips to the hex the design spec
     * names it by.
     *
     * Tolerance is 2/255 per channel, and that is a fact about the spec, not
     * a loosened check. The spec gives INK as BOTH `#14121A` and
     * `hsl(260 18% 9%)`, and those two are not the same number: the HSL
     * triple rasterises to #16131B, 2/255 away on red and blue. The HSL form
     * is what the stylesheet ships and therefore what the browser paints, so
     * it is normative here; the tolerance records the spec's own rounding
     * rather than papering over a token that drifted. RED and WHITE round
     * trip exactly, and would still pass at a tolerance of 0.
     */
    const assertIsHex = (scope: Record<string, string>, name: string, hex: string) => {
        const asRgb = composite(token(scope, name), '0 0% 100%');
        const want = hexToRgb(hex);
        for (const channel of ['r', 'g', 'b'] as const) {
            assert.ok(
                Math.abs(asRgb[channel] - want[channel]) <= 2,
                `${name} ${channel}=${asRgb[channel]}, expected ${want[channel]} (${hex})`,
            );
        }
        assert.equal(parseHsl(token(scope, name)).a, 1, `${name} must be opaque`);
    };

    await t.test('--brand is BLUE #155DFC — primary fill', () => {
        assertIsHex(themes.light, '--brand', BLUE);
        assertIsHex(themes.light, '--primary', BLUE);
    });

    await t.test('--brand-2 is BLACK — dominant brand ground', () => {
        assertIsHex(themes.light, '--brand-2', BLACK);
    });

    await t.test('BLACK is the light-theme body ink and the dark-theme ground', () => {
        assertIsHex(themes.light, '--foreground', BLACK);
        assertIsHex(themes.dark, '--background', BLACK);
        assert.equal(token(themes.dark, '--background'), token(themes.light, '--brand-2'));
    });

    await t.test('identity does not follow the OS theme', () => {
        // Brand identity tokens stay fixed across OS theme (see wordmark.tsx).
        for (const name of ['--brand', '--brand-2', '--brand-ink', '--primary', '--primary-foreground']) {
            assert.equal(
                token(themes.light, name),
                token(themes.dark, name),
                `${name} differs between themes`,
            );
        }
    });

    await t.test('fest orange is not used as primary brand chrome', () => {
        // Orange #FF691C is an accent for stacked cards, not --primary.
        const brandish = [
            '--brand',
            '--brand-2',
            '--primary',
            '--primary-emphasis',
            '--accent',
            '--accent-foreground',
            '--ring',
            '--sidebar-primary-foreground',
        ];
        for (const themeName of ['light', 'dark'] as const) {
            for (const name of brandish) {
                const { h, s } = parseHsl(token(themes[themeName], name));
                const isRetiredBand = h >= 20 && h <= 45 && s > 0.35;
                assert.ok(
                    !isRetiredBand,
                    `${name} (${themeName}) is h=${h} s=${s} — inside the retired accent band`,
                );
            }
        }
    });
});

// ── The stylesheet parse ────────────────────────────────────────────────────

test('theme tokens are read from the shipped stylesheet', async (t) => {
    await t.test('both theme scopes are present and populated', () => {
        assert.ok(Object.keys(themes.light).length > 25);
        assert.ok(Object.keys(themes.dark).length > 25);
    });

    await t.test('dark inherits every token it does not override', () => {
        // .dark only redefines what differs. Measuring the block alone would
        // test a palette no browser ever renders — and would skip exactly the
        // inherited tokens where an unreadable value could hide.
        assert.equal(themes.dark['--brand'], themes.light['--brand']);
        assert.equal(themes.dark['--sidebar-background'], themes.light['--sidebar-background']);
        assert.notEqual(themes.dark['--background'], themes.light['--background']);
    });

    await t.test('a token mentioned only in a comment is not read as a declaration', () => {
        // The :root block's prose names --primary-emphasis, --primary and
        // --verdict-duplicate several times; comment stripping is what keeps
        // those mentions from being parsed as live values.
        assert.equal(themes.light['--primary-emphasis'], '221 85% 38%');
        assert.equal(themes.dark['--primary-emphasis'], '221 100% 70%');
    });
});

// ── The audit ───────────────────────────────────────────────────────────────

for (const themeName of ['light', 'dark'] as const) {
    test(`WCAG AA — ${themeName} theme`, async (t) => {
        for (const pair of PAIRS) {
            await t.test(`${pair.name} clears ${pair.threshold}:1`, () => {
                measurements++;
                const result = measurePair(themes[themeName], pair);
                assert.ok(
                    result.pass,
                    `${pair.name} (${themeName}): ${round2(result.ratio)}:1, needs ${pair.threshold}:1 ` +
                        `— ${pair.fg} on ${pair.bg}`,
                );
            });
        }
    });
}

test('WCAG AA — gate scan surface', async (t) => {
    for (const pair of GATE_PAIRS) {
        await t.test(`${pair.name} clears ${pair.threshold}:1`, () => {
            measurements++;
            const result = measureLiteralPair(pair);
            assert.ok(
                result.pass,
                `${pair.name}: ${round2(result.ratio)}:1, needs ${pair.threshold}:1`,
            );
        });
    }

    await t.test('the audited verdict fills are the ones index.css actually ships', () => {
        // GATE_PAIRS holds literals because .gate-surface is theme-independent.
        // That duplication is only safe while it is checked.
        const mismatches = verdictTokensMatch(themes.light);
        assert.deepEqual(
            mismatches,
            [],
            'verdict tokens drifted from the audit: ' + JSON.stringify(mismatches),
        );
        assert.deepEqual(verdictTokensMatch(themes.dark), []);
    });
});

// ── §2 of the design spec, measured rather than quoted ──────────────────────
//
// The spec states five contrast facts about the Red/White/Ink palette. Every
// one of them is recomputed here from the shipped tokens. Where the spec's
// stated figure and the measurement disagree, the MEASUREMENT wins and the
// gap is recorded in the assertion message — a design document is not a
// colorimeter.

/**
 * SPEC_PAIRS mirrors the design spec's §2 rules. Kept here rather than in
 * contrast-audit.js because these are assertions about the PALETTE's rules,
 * not about a rendered surface an audit report should tabulate.
 */
const SPEC_PAIRS = [
    { name: 'Tdev black body text on white', fg: BLACK, bg: WHITE, threshold: AA_NORMAL_TEXT },
    { name: 'Tdev white body text on black', fg: WHITE, bg: BLACK, threshold: AA_NORMAL_TEXT },
    { name: 'Tdev blue emphasis text on white', fg: '221 85% 38%', bg: WHITE, threshold: AA_NORMAL_TEXT },
    { name: 'Tdev blue emphasis text on muted', fg: '221 85% 38%', bg: '220 14% 96%', threshold: AA_NORMAL_TEXT },
    { name: 'Tdev white label on blue primary fill', fg: WHITE, bg: BLUE, threshold: AA_NORMAL_TEXT },
    { name: 'Tdev white on blue (non-text graphics)', fg: WHITE, bg: BLUE, threshold: AA_NON_TEXT },
    { name: 'Tdev blue as large display type on white', fg: BLUE, bg: WHITE, threshold: AA_LARGE_TEXT },
];

test('design spec §2 — the palette rules, recomputed', async (t) => {
    for (const pair of SPEC_PAIRS) {
        await t.test(`${pair.name} clears ${pair.threshold}:1`, () => {
            const measured = round2(ratio(pair.fg, pair.bg));
            assert.ok(
                meets(measured, pair.threshold),
                `${pair.name}: measured ${measured}:1, needs ${pair.threshold}:1`,
            );
        });
    }

    await t.test('the spec examined every rule it claims to', () => {
        assert.equal(SPEC_PAIRS.length, 7);
    });
});

// ── The rules the palette is built on ───────────────────────────────────────

test('palette invariants', async (t) => {
    await t.test('raw primary blue is not used as body text on light grounds', () => {
        for (const ground of ['--background', '--card', '--muted']) {
            const r = ratio(token(themes.light, '--primary'), token(themes.light, ground));
            assert.ok(
                !meets(r, AA_NORMAL_TEXT),
                `--primary on ${ground} measured ${round2(r)}:1 — use --primary-emphasis for text`,
            );
        }
    });

    await t.test('white is the label ink on the blue primary control', () => {
        for (const themeName of ['light', 'dark'] as const) {
            const scope = themes[themeName];
            const shipped = ratio(token(scope, '--primary-foreground'), token(scope, '--primary'));
            assert.ok(
                meets(shipped, AA_NORMAL_TEXT),
                `--primary-foreground on --primary (${themeName}) is ${round2(shipped)}:1`,
            );
        }
    });

    await t.test('brand ink and the focus ring are legible in both themes', () => {
        for (const themeName of ['light', 'dark'] as const) {
            const scope = themes[themeName];
            for (const ground of ['--background', '--card', '--muted']) {
                const ink = ratio(token(scope, '--primary-emphasis'), token(scope, ground));
                assert.ok(
                    meets(ink, AA_NORMAL_TEXT),
                    `--primary-emphasis on ${ground} (${themeName}) is ${round2(ink)}:1`,
                );
                const ring = ratio(token(scope, '--ring'), token(scope, ground));
                assert.ok(
                    meets(ring, AA_NON_TEXT),
                    `--ring on ${ground} (${themeName}) is ${round2(ring)}:1`,
                );
            }
        }
    });

    await t.test('danger stays distinguishable from the brand blue', () => {
        const hueDistance = (a: string, b: string) => {
            const d = Math.abs(parseHsl(a).h - parseHsl(b).h);
            return Math.min(d, 360 - d);
        };
        for (const themeName of ['light', 'dark'] as const) {
            const scope = themes[themeName];
            const apart = hueDistance(token(scope, '--destructive'), token(scope, '--primary'));
            assert.ok(apart >= 15, `--destructive is only ${apart}° from --primary (${themeName})`);
        }

        const light = themes.light;
        const step = ratio(token(light, '--destructive'), token(light, '--primary'));
        assert.ok(round2(step) >= 2, `light: destructive and primary fills are only ${round2(step)}:1 apart`);

        const brandInk = relativeLuminance(
            composite(token(light, '--primary-foreground'), token(light, '--primary')),
        );
        const dangerInk = relativeLuminance(
            composite(token(light, '--destructive-foreground'), token(light, '--destructive')),
        );
        assert.ok(
            Math.abs(brandInk - dangerInk) > 0.3,
            'light: the brand fill and the destructive fill carry the same ink',
        );
    });

    await t.test('every verdict flood carries its text at AA in both themes', () => {
        for (const themeName of ['light', 'dark'] as const) {
            const scope = themes[themeName];
            for (const v of ['--verdict-admit', '--verdict-reject', '--verdict-duplicate']) {
                const r = ratio(token(scope, '--verdict-ink'), token(scope, v));
                assert.ok(meets(r, AA_NORMAL_TEXT), `${v} (${themeName}) carries ink at ${round2(r)}:1`);
            }
        }
    });

    await t.test('the verdict palette is frozen — and is what it always was', () => {
        // A gate runs the same screen at dusk and at noon. The answer it gives
        // must not change shade because of a theme toggle nobody touched — and
        // it must not have been swept along by the brand repaint either. These
        // are pinned to literals ON PURPOSE: this is the one table in the app
        // that a palette change is never allowed to reach.
        const frozen = {
            '--verdict-admit': '150 70% 29%',
            '--verdict-reject': '0 78% 46%',
            '--verdict-duplicate': '28 95% 34%',
            '--verdict-ink': '0 0% 100%',
        };
        for (const [name, value] of Object.entries(frozen)) {
            assert.equal(token(themes.light, name), value, `${name} moved`);
            assert.equal(token(themes.dark, name), value, `${name} moved in dark`);
        }
    });

    await t.test('"already scanned" is held clear of the brand blue', () => {
        const brandHue = parseHsl(token(themes.light, '--brand')).h;
        const dupHue = parseHsl(token(themes.light, '--verdict-duplicate')).h;
        const distance = Math.min(Math.abs(brandHue - dupHue), 360 - Math.abs(brandHue - dupHue));
        assert.ok(distance >= 20, `brand h=${brandHue}, duplicate h=${dupHue}, apart by ${distance}`);
    });

    await t.test('accent line tint matches brand hue and stays visible', () => {
        const DECORATION_VISIBLE = 1.5;
        for (const themeName of ['light', 'dark'] as const) {
            const scope = themes[themeName];
            const perf = token(scope, '--perforation');
            assert.ok(parseHsl(perf).a < 1, `--perforation (${themeName}) should be a tint, not a solid`);
            assert.equal(parseHsl(perf).h, parseHsl(token(scope, '--brand')).h, 'perforation is not the brand hue');
            const r = ratio(perf, token(scope, '--background'));
            assert.ok(
                meets(r, DECORATION_VISIBLE),
                `--perforation on the page (${themeName}) is ${round2(r)}:1`,
            );
        }
        assert.notEqual(token(themes.light, '--perforation'), token(themes.dark, '--perforation'));
    });
});

// ── The 12px type floor ─────────────────────────────────────────────────────

test('type floor', async (t) => {
    await t.test('nothing in the stylesheet sets type below 12px', () => {
        // A suite-wide floor. Enforced by reading the stylesheet rather than
        // by convention, because "don't use text-[11px]" is not a mechanism.
        const offenders = [];
        for (const m of css.matchAll(/font-size:\s*([\d.]+)(px|rem)/g)) {
            const px = m[2] === 'rem' ? Number(m[1]) * 16 : Number(m[1]);
            if (px < 12) offenders.push(m[0]);
        }
        assert.deepEqual(offenders, [], `sub-12px type in index.css: ${offenders.join(', ')}`);
    });

    await t.test('the tailwind display scale never drops below 12px', () => {
        const config = readFileSync(join(here, '..', '..', 'tailwind.config.ts'), 'utf8');
        const scale = config.slice(config.indexOf('fontSize: {'), config.indexOf('boxShadow: {'));
        const offenders = [];
        for (const m of scale.matchAll(/'([\d.]+)rem'/g)) {
            if (Number(m[1]) * 16 < 12) offenders.push(m[0]);
        }
        assert.deepEqual(offenders, [], `sub-12px step in the display scale: ${offenders.join(', ')}`);
    });
});

// ── The count ───────────────────────────────────────────────────────────────

test('measurements taken', async (t) => {
    await t.test('the audit tables are the size they are supposed to be', () => {
        // If a table is emptied or an import silently resolves to `[]`, every
        // loop above passes by examining nothing. These three numbers are the
        // only thing standing between that and a green build.
        assert.equal(PAIRS.length, 32, 'the audited surface pairs changed count');
        assert.equal(GATE_PAIRS.length, 5, 'the gate-surface pairs changed count');
        assert.equal(SPEC_PAIRS.length, 7, 'the design-spec §2 rules changed count');
    });

    await t.test('this file computed every ratio it was supposed to', () => {
        // 32 surface pairs × 2 themes, 5 gate pairs, 7 spec rules, and 33
        // ratios computed inline by the maths and invariant tests:
        //   5  contrast maths (2 + 1 + 2)
        //   3  red-as-body-text, over page / card / bone
        //   4  white-is-not-the-ink, 2 themes × (white, shipped ink)
        //  12  brand ink + focus ring, 2 themes × 3 grounds × 2 tokens
        //   1  the light-theme step between the two red fills
        //   6  verdict floods, 2 themes × 3
        //   2  the perforation on each ground
        const INLINE = 31;
        const expected = PAIRS.length * 2 + GATE_PAIRS.length + SPEC_PAIRS.length + INLINE;
        assert.equal(
            measurements,
            expected,
            `computed ${measurements} ratios, expected ${expected} — a check was added or lost`,
        );
    });
});
