// lib/money.js
//
// Tdev Festival is country- and currency-agnostic: there is no privileged
// currency, and "cents" is not a universal truth. ISO-4217 currencies do
// NOT all have two decimal places — JPY, KRW, VND, CLP, ISK (and others)
// have ZERO, while KWD, BHD, JOD, OMR, TND have THREE. Every backend
// amount is an integer count of the currency's own MINOR unit
// (`*_minor` fields) plus the ISO-4217 `currency` it is denominated in
// (see internal/money, the Go source of truth this file mirrors).
//
// This module is the ONLY place the frontend should convert a minor-unit
// integer into a displayable amount. Never hardcode `/ 100`, a currency
// symbol like `R `/`$`, or a fallback currency like `'ZAR'` anywhere else
// in web/src — route every money display through `formatMoney` (or
// `minorToMajorNumber`/`minorToMajorString` if you need the raw number
// rather than a fully-formatted, localized string).
//
// # The locale/symbol pitfall this file exists to avoid
//
// `Intl.NumberFormat(locale, { style: 'currency', currency })` renders
// "ZAR 450.00" instead of "R 450.00" whenever the caller's locale doesn't
// itself correspond to a country that uses that currency (e.g. an
// `en-US` browser viewing a ZAR-priced event) — `Intl` falls back to
// printing the ISO code instead of the symbol. Passing
// `currencyDisplay: 'narrowSymbol'` fixes this: it always prefers the
// currency's own symbol (R, ¥, £, €, $, ...) regardless of the
// formatting locale. A currency with no widely-recognised symbol (KWD,
// BHD, ...) still falls back to its ISO code either way — that's honest,
// not a bug (internal/money's own `Amount.String()` does the same:
// "<major> <CUR>").

/**
 * Zero-decimal currencies (no minor unit at all — an integer IS the
 * major-unit amount). Mirrors internal/money/currency.go's
 * `currencyDefs` table exactly; keep in sync by hand if that table ever
 * changes.
 */
const ZERO_DECIMAL_CURRENCIES = new Set([
    'BIF', 'CLP', 'DJF', 'GNF', 'ISK', 'JPY', 'KMF', 'KRW', 'PYG', 'RWF',
    'UGX', 'VND', 'VUV', 'XAF', 'XOF', 'XPF',
]);

/**
 * Three-decimal currencies. Mirrors internal/money/currency.go.
 */
const THREE_DECIMAL_CURRENCIES = new Set(['BHD', 'IQD', 'JOD', 'KWD', 'LYD', 'OMR', 'TND']);

/**
 * getExponent returns how many digits follow the decimal point when
 * `currency` is displayed in its major unit: 0 for JPY, 3 for KWD, 2 for
 * everything else (the ISO-4217 default). `currency` is normalized
 * case-insensitively; an empty/missing code falls back to 2 rather than
 * throwing, since display code should degrade gracefully rather than
 * crash a page over a missing currency — validation belongs at the point
 * data enters the system (the Go backend), not in a formatting helper.
 *
 * @param {string} currency ISO-4217 alpha-3 code (any case).
 * @returns {number}
 */
export function getExponent(currency: string | null | undefined): number {
    const code = String(currency || '').trim().toUpperCase();
    if (ZERO_DECIMAL_CURRENCIES.has(code)) return 0;
    if (THREE_DECIMAL_CURRENCIES.has(code)) return 3;
    return 2;
}

/**
 * minorToMajorString renders an integer minor-unit amount as an exact
 * decimal STRING using currency's own exponent — e.g. minorToMajorString
 * (450000, 'JPY') -> "450000", minorToMajorString(1234, 'USD') -> "12.34",
 * minorToMajorString(32750, 'KWD') -> "32.750". Built on integer/string
 * arithmetic (never a floating-point division) so there is no rounding
 * surprise before the value is handed to Intl.NumberFormat.
 *
 * @param {number} minor
 * @param {string} currency
 * @returns {string}
 */
export function minorToMajorString(minor: number, currency: string): string {
    const exp = getExponent(currency);
    const n = Number.isFinite(minor) ? Math.trunc(minor) : 0;
    const neg = n < 0;
    const mag = String(Math.abs(n));

    if (exp === 0) {
        return (neg ? '-' : '') + mag;
    }

    const padded = mag.padStart(exp + 1, '0');
    const intPart = padded.slice(0, padded.length - exp);
    const fracPart = padded.slice(padded.length - exp);
    return (neg ? '-' : '') + intPart + '.' + fracPart;
}

/**
 * minorToMajorNumber is minorToMajorString parsed back into a JS number,
 * for callers that need the numeric major-unit value itself (charts,
 * arithmetic display, `<input type="number">` defaults, ...) rather than
 * a formatted string. Prefer formatMoney for anything user-facing.
 *
 * @param {number} minor
 * @param {string} currency
 * @returns {number}
 */
export function minorToMajorNumber(minor: number, currency: string): number {
    return Number(minorToMajorString(minor, currency));
}

/**
 * majorStringToMinor is the inverse of minorToMajorString: parses a
 * decimal major-unit string (e.g. "45", "12.34", "32.750") into an
 * integer minor-unit amount, using currency's own exponent — never a
 * hardcoded 100. This is what a price-entry form should use to convert
 * organiser input into `price_minor` before sending it to the API.
 *
 * Returns `null` for input that isn't a plain non-negative decimal number,
 * or that has MORE fractional digits than the currency allows (this is
 * strict, like internal/money.ParseMajor — it never silently rounds/
 * truncates a price the organiser typed).
 *
 * @param {string} major
 * @param {string} currency
 * @returns {number|null}
 */
export function majorStringToMinor(major: string | null | undefined, currency: string): number | null {
    const exp = getExponent(currency);
    const s = String(major ?? '').trim();
    if (s === '') return null;
    if (!/^\d+(\.\d+)?$/.test(s)) return null;

    const [intPart, fracPart = ''] = s.split('.');
    if (fracPart.length > exp) return null;

    const paddedFrac = fracPart.padEnd(exp, '0');
    const combined = (intPart + paddedFrac).replace(/^0+(?=\d)/, '');
    if (!/^\d+$/.test(combined)) return null;

    const n = Number(combined);
    return Number.isSafeInteger(n) ? n : null;
}

/**
 * decimalInputPattern returns a RegExp matching a partial-or-complete
 * decimal string valid for currency's own exponent — e.g. exponent 0
 * (JPY) only allows whole numbers, exponent 3 (KWD) allows up to three
 * fractional digits. Use this to constrain a price `<input>` as the
 * organiser types, instead of a hardcoded "up to 2 decimals" regex.
 *
 * @param {string} currency
 * @returns {RegExp}
 */
export function decimalInputPattern(currency: string): RegExp {
    const exp = getExponent(currency);
    if (exp <= 0) return /^\d*$/;
    return new RegExp(`^\\d*\\.?\\d{0,${exp}}$`);
}

/**
 * resolveLocale picks a sensible formatting locale: the caller's explicit
 * choice, else the browser's own preferred language, else a safe
 * hardcoded fallback. This does NOT need to "match" the currency —
 * formatMoney's `currencyDisplay: 'narrowSymbol'` is what makes the
 * symbol correct regardless of locale; this just governs digit grouping/
 * decimal-separator conventions (1,234.56 vs 1.234,56).
 *
 * @param {string|undefined} [locale]
 * @returns {string}
 */
function resolveLocale(locale?: string): string {
    if (locale) return locale;
    if (typeof navigator !== 'undefined' && navigator.language) return navigator.language;
    return 'en-US';
}

/**
 * formatMoney is the ONE way to render a minor-unit amount as a
 * user-facing string. Always uses the currency's own real exponent
 * (never a hardcoded 100) and always prefers the currency's own symbol
 * over its ISO code (`currencyDisplay: 'narrowSymbol'`), regardless of
 * whether the formatting locale "matches" the currency.
 *
 * @param {number} minor Integer minor-unit amount (e.g. price_minor,
 *   total_minor, revenue_minor).
 * @param {string} currency ISO-4217 alpha-3 code.
 * @param {{ locale?: string }} [opts]
 * @returns {string} e.g. "R 450.00", "¥4,500", "35.939 KWD" (a currency
 *   with no widely-recognised symbol falls back to printing its ISO
 *   code — that's honest, not a bug).
 */
export function formatMoney(minor: number, currency: string | null | undefined, opts: { locale?: string } = {}): string {
    const code = String(currency || '').trim().toUpperCase();
    const exp = getExponent(code);
    const major = minorToMajorNumber(minor, code);
    const locale = resolveLocale(opts.locale);

    if (!code) {
        // No currency at all: there is nothing honest to render as a
        // symbol/code, so fall back to a plain number rather than
        // pretending a currency was specified.
        return new Intl.NumberFormat(locale, {
            minimumFractionDigits: exp,
            maximumFractionDigits: exp,
        }).format(major);
    }

    try {
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: code,
            currencyDisplay: 'narrowSymbol',
            minimumFractionDigits: exp,
            maximumFractionDigits: exp,
        }).format(major);
    } catch {
        // An unrecognised/malformed code (shouldn't happen for data that
        // came from a backend that validates via internal/money, but
        // never let a formatting helper throw and blank a whole page) —
        // fall back to "<major> <CODE>", mirroring internal/money's own
        // Amount.String() fallback shape.
        return minorToMajorString(minor, code) + ' ' + code;
    }
}
