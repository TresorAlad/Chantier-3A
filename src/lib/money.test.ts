// Money: minor units, real ISO-4217 exponents, and the width invariant that
// keeps a column of figures from jumping.
//
// `lib/money.js` was written and left untested. It is the file that decides
// what a buyer is charged, so it gets a suite — with particular attention to
// the two things that are wrong in most ticketing code: assuming every
// currency has two decimal places, and doing minor->major with floating point.

import test from 'node:test';
import assert from 'node:assert/strict';

import {
    getExponent,
    minorToMajorString,
    minorToMajorNumber,
    majorStringToMinor,
    decimalInputPattern,
    formatMoney,
} from './money.ts';

// ── Exponents ───────────────────────────────────────────────────────────────

test('ISO-4217 exponents are per-currency, not universally 2', async (t) => {
    await t.test('zero-decimal currencies', () => {
        // An integer IS the major amount. Dividing these by 100 — the thing
        // every hardcoded `/ 100` does — undercharges by 100x.
        for (const code of ['JPY', 'KRW', 'VND', 'CLP', 'ISK', 'XOF']) {
            assert.equal(getExponent(code), 0, code);
        }
    });

    await t.test('three-decimal currencies', () => {
        for (const code of ['KWD', 'BHD', 'JOD', 'OMR', 'TND', 'IQD', 'LYD']) {
            assert.equal(getExponent(code), 3, code);
        }
    });

    await t.test('everything else is 2', () => {
        for (const code of ['USD', 'EUR', 'ZAR', 'GBP', 'NGN']) {
            assert.equal(getExponent(code), 2, code);
        }
    });

    await t.test('case-insensitive, and degrades rather than throwing', () => {
        assert.equal(getExponent('jpy'), 0);
        assert.equal(getExponent(' KwD '), 3);
        // A formatting helper must never be the thing that blanks a page.
        assert.equal(getExponent(''), 2);
        assert.equal(getExponent(undefined), 2);
    });
});

// ── Minor -> major ──────────────────────────────────────────────────────────

test('minor units convert exactly, never through a float', async (t) => {
    await t.test('the standard two-decimal case', () => {
        assert.equal(minorToMajorString(1234, 'USD'), '12.34');
        assert.equal(minorToMajorString(5, 'USD'), '0.05');
        assert.equal(minorToMajorString(0, 'USD'), '0.00');
        assert.equal(minorToMajorString(100, 'USD'), '1.00');
    });

    await t.test('zero-decimal currencies pass the integer straight through', () => {
        assert.equal(minorToMajorString(450000, 'JPY'), '450000');
        assert.equal(minorToMajorString(0, 'KRW'), '0');
    });

    await t.test('three-decimal currencies keep all three', () => {
        assert.equal(minorToMajorString(32750, 'KWD'), '32.750');
        assert.equal(minorToMajorString(7, 'BHD'), '0.007');
    });

    await t.test('negatives keep their sign and their magnitude', () => {
        assert.equal(minorToMajorString(-1234, 'USD'), '-12.34');
        assert.equal(minorToMajorString(-5, 'KWD'), '-0.005');
        assert.equal(minorToMajorString(-450, 'JPY'), '-450');
    });

    await t.test('values a float would get wrong come out exact', () => {
        // 0.1 + 0.2 territory. String/integer arithmetic has no opinion about
        // binary fractions, which is the entire reason it is used here.
        assert.equal(minorToMajorString(1e15 + 7, 'USD'), '10000000000000.07');
        assert.equal(minorToMajorNumber(1234, 'USD'), 12.34);
    });
});

// ── Major -> minor (what an organiser types) ────────────────────────────────

test('price entry parses strictly and never silently rounds', async (t) => {
    await t.test('round trips through the currency exponent', () => {
        for (const [major, code, minor] of [
            ['12.34', 'USD', 1234],
            ['450000', 'JPY', 450000],
            ['32.750', 'KWD', 32750],
            ['0', 'USD', 0],
            ['45', 'USD', 4500],
        ] as Array<[string, string, number]>) {
            assert.equal(majorStringToMinor(major, code), minor, `${major} ${code}`);
            assert.equal(minorToMajorNumber(minor, code), Number(major));
        }
    });

    await t.test('too many fractional digits is rejected, not truncated', () => {
        // Silently turning 12.349 into 1234 would charge a price the organiser
        // never typed.
        assert.equal(majorStringToMinor('12.349', 'USD'), null);
        assert.equal(majorStringToMinor('450.5', 'JPY'), null);
        assert.equal(majorStringToMinor('1.2345', 'KWD'), null);
    });

    await t.test('non-numeric input is rejected', () => {
        for (const bad of ['', '  ', 'abc', '12,34', '-5', '1e3', '12.', '.5', null, undefined]) {
            assert.equal(majorStringToMinor(bad, 'USD'), null, JSON.stringify(bad));
        }
    });

    await t.test('the input pattern matches the currency it is for', () => {
        assert.ok(decimalInputPattern('JPY').test('450'));
        assert.ok(!decimalInputPattern('JPY').test('450.5'));
        assert.ok(decimalInputPattern('KWD').test('32.750'));
        assert.ok(!decimalInputPattern('KWD').test('32.7501'));
        assert.ok(decimalInputPattern('USD').test('12.3'), 'partial input while typing');
    });
});

// ── Display ─────────────────────────────────────────────────────────────────

test('formatMoney renders the currency honestly', async (t) => {
    await t.test('uses the currency symbol even when the locale does not match', () => {
        // The pitfall the module exists for: an en-US browser viewing a
        // ZAR-priced event renders "ZAR 450.00" without narrowSymbol.
        const zar = formatMoney(45000, 'ZAR', { locale: 'en-US' });
        assert.ok(zar.includes('R'), zar);
        assert.ok(!zar.includes('ZAR'), zar);
    });

    await t.test('respects the currency exponent in the output', () => {
        assert.ok(formatMoney(450000, 'JPY', { locale: 'en-US' }).includes('450,000'));
        assert.ok(!formatMoney(450000, 'JPY', { locale: 'en-US' }).includes('.'));
        assert.ok(formatMoney(32750, 'KWD', { locale: 'en-US' }).includes('32.750'));
    });

    await t.test('no currency renders a bare number rather than inventing one', () => {
        // Falling back to a hardcoded 'ZAR'/'USD' would print a price in a
        // currency nobody chose.
        const out = formatMoney(1234, '', { locale: 'en-US' });
        assert.equal(out, '12.34');
    });

    await t.test('an unusable currency code degrades instead of throwing', () => {
        const out = formatMoney(1234, 'NOTACURRENCY', { locale: 'en-US' });
        assert.match(out, /12\.34/);
        assert.match(out, /NOTACURRENCY/);
    });
});

// ── The column invariant ────────────────────────────────────────────────────

test('a column of figures does not change width as its values change', async (t) => {
    // Tabular figures (the `.tnum` utility) make every DIGIT the same advance
    // width in the rendered font. That guarantee is only useful if the
    // formatted STRINGS are also structurally stable — same digit count in,
    // same character count out. If formatting itself varied, no font feature
    // would save the column.

    await t.test('same magnitude, different digits, identical length', () => {
        const codes = ['USD', 'ZAR', 'EUR', 'JPY', 'KWD'];
        for (const code of codes) {
            const lengths = new Set();
            // Every 4-digit-minor value: 1111, 2222, ... 9999 plus 1000/1999.
            for (const minor of [1000, 1111, 1999, 5555, 8888, 9999]) {
                lengths.add(formatMoney(minor, code, { locale: 'en-US' }).length);
            }
            assert.equal(lengths.size, 1, `${code} produced widths ${[...lengths].join(',')}`);
        }
    });

    await t.test('a running total ticking over a digit boundary stays stable', () => {
        // 19 -> 20 is the classic case: with proportional figures the "1"
        // is narrower than the "2" and the whole row shifts. The string length
        // is unchanged, so the only variable left is the font feature.
        const a = formatMoney(1900, 'USD', { locale: 'en-US' });
        const b = formatMoney(2000, 'USD', { locale: 'en-US' });
        assert.equal(a.length, b.length);
    });

    await t.test('crossing a thousands separator legitimately changes width', () => {
        // Stated rather than asserted away: 999.99 -> 1,000.00 IS wider, in
        // any font. That is what right-aligning a money column handles, and
        // why MoneyCell aligns right rather than left.
        const under = formatMoney(99999, 'USD', { locale: 'en-US' });
        const over = formatMoney(100000, 'USD', { locale: 'en-US' });
        assert.ok(over.length > under.length, `${under} -> ${over}`);
    });

    await t.test('different currencies genuinely differ in width', () => {
        // The reason a mixed-currency column must be right-aligned: these are
        // not the same length and no font feature makes them so.
        const widths = ['JPY', 'USD', 'KWD'].map((c) => formatMoney(123456, c, { locale: 'en-US' }).length);
        assert.ok(new Set(widths).size > 1, `widths ${widths.join(',')}`);
    });
});
