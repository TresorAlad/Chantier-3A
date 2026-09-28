// lib/theme-tokens.js
//
// Reads the design tokens out of the real `src/index.css` text.
//
// The point is that the accessibility gate measures the STYLESHEET THE APP
// SHIPS, not a second copy of the palette maintained beside it. A duplicated
// token table would drift the first time somebody nudged a colour, and the
// gate would keep passing while the app went dark — the exact failure mode
// this whole exercise is meant to catch.
//
// Deliberately a plain text parse rather than a CSS AST dependency: the input
// is one file we control, the shape is `--name: value;` inside a known
// selector, and this has to run under bare `node --test` with nothing built.

/**
 * extractBlock returns the raw body of the first CSS block whose selector
 * matches `selector` exactly, tracking brace depth so a nested block does not
 * end the match early.
 *
 * @param css
 * @param selector e.g. ':root' or '.dark'
 * @returns block body, without the outer braces
 */
function extractBlock(css: string, selector: string): string {
    // Match the selector only where it stands alone before a brace, so
    // `:root` does not also match `:root[data-x]` and `.dark` does not match
    // `.dark-mode`.
    const re = new RegExp(`(^|[}\\s])${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{`, 'm');
    const start = css.search(re);
    if (start === -1) throw new Error(`theme-tokens: no ${selector} block found`);

    const open = css.indexOf('{', start);
    let depth = 0;
    for (let i = open; i < css.length; i++) {
        if (css[i] === '{') depth++;
        else if (css[i] === '}') {
            depth--;
            if (depth === 0) return css.slice(open + 1, i);
        }
    }
    throw new Error(`theme-tokens: unterminated ${selector} block`);
}

/**
 * parseCustomProperties pulls every `--name: value;` declaration out of a
 * block body into a plain object. Comments are stripped first so a token
 * mentioned inside an explanatory comment cannot masquerade as a live
 * declaration.
 */
function parseCustomProperties(body: string): Record<string, string> {
    const withoutComments = body.replace(/\/\*[\s\S]*?\*\//g, '');
    const out: Record<string, string> = {};
    const re = /(--[a-zA-Z0-9-]+)\s*:\s*([^;]+);/g;
    let m;
    while ((m = re.exec(withoutComments)) !== null) {
        const [, name, value] = m;
        // Both groups are mandatory in the pattern above (neither is `?`), so
        // a successful match always populates them — this is a narrowing
        // check against noUncheckedIndexedAccess, not a real possibility.
        if (name === undefined || value === undefined) continue;
        out[name] = value.trim();
    }
    return out;
}

export interface ThemeTokens {
    light: Record<string, string>;
    dark: Record<string, string>;
}

/**
 * readThemeTokens parses `index.css` text into the two theme scopes the app
 * actually renders under.
 *
 * `dark` is returned MERGED over `light`, which mirrors the cascade at
 * runtime: `.dark` only redefines the tokens that differ, and everything it
 * omits keeps its `:root` value. Measuring the `.dark` block alone would test
 * a palette that never exists in a browser — and would silently skip any
 * token the dark theme inherits, which is precisely where an unreadable
 * inherited value would hide.
 *
 * @param css contents of src/index.css
 */
export function readThemeTokens(css: string): ThemeTokens {
    const light = parseCustomProperties(extractBlock(css, ':root'));
    const darkOverrides = parseCustomProperties(extractBlock(css, '.dark'));
    return { light, dark: { ...light, ...darkOverrides } };
}

/**
 * token looks up a custom property for a theme and fails loudly if it is
 * absent. A missing token must never be scored as black-on-black or skipped:
 * either would turn a renamed variable into a silently passing gate.
 *
 * @param name with or without the leading `--`
 */
export function token(scope: Record<string, string>, name: string): string {
    const key = name.startsWith('--') ? name : `--${name}`;
    const value = scope[key];
    if (value === undefined) throw new Error(`theme-tokens: ${key} is not defined`);
    return value;
}
