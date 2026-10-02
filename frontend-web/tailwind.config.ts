import defaultTheme from 'tailwindcss/defaultTheme';
import plugin from 'tailwindcss/plugin';
import tailwindcssAnimate from 'tailwindcss-animate';
import tailwindcssTypography from '@tailwindcss/typography';

// WCAG 2.5.8 (Target Size, Minimum, AA) sizes the TARGET, not the artwork.
// A checkbox and a radio are drawn at 16px because that is what reads
// correctly beside a line of 14px label text — growing the box to 24px to
// satisfy the criterion would be fixing the wrong number.
//
// `hit-area-24` is the right number: a transparent 24x24 pseudo-element
// centred on the control, at zero visual cost. It lives here, as ONE named
// utility, rather than as a run of `after:*` classes copy-pasted into each
// primitive — two hand-maintained copies of a hit area are two hit areas
// that will eventually differ, and the whole point is that the number is
// exact.
//
// It is EXACTLY 24, and that is a ceiling as much as a floor. Two adjacent
// expanded targets whose areas overlap are worse than the small targets they
// replaced: a tap near the boundary lands on the wrong control, silently.
// 24 is the standard's minimum and, paired with the `m-1` the primitives
// carry, the largest value that still guarantees adjacent controls' areas
// abut rather than intersect. Raising it here would quietly break that
// guarantee everywhere at once — see checkbox.jsx.
const hitArea = plugin((api) => {
    // Called through `api` rather than destructured — Tailwind's own
    // PluginAPI types addUtilities as an interface method, which
    // no-unbound-method treats as potentially `this`-dependent regardless
    // of whether it actually is; calling it through its receiver sidesteps
    // that rather than asserting it away.
    api.addUtilities({
        '.hit-area-24': {
            position: 'relative',
            '&::after': {
                content: '""',
                position: 'absolute',
                left: '50%',
                top: '50%',
                height: '1.5rem',
                width: '1.5rem',
                transform: 'translate(-50%, -50%)',
            },
        },
    });
});

/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ['class'],
    content: [
        './pages/**/*.{js,jsx,ts,tsx}',
        './components/**/*.{js,jsx,ts,tsx}',
        './app/**/*.{js,jsx,ts,tsx}',
        './src/**/*.{js,jsx,ts,tsx}',
    ],
    theme: {
        container: {
            center: true,
            padding: '2rem',
            screens: {
                '2xl': '1400px',
            },
        },
        extend: {
            colors: {
                border: 'hsl(var(--border))',
                input: 'hsl(var(--input))',
                ring: 'hsl(var(--ring))',
                background: 'hsl(var(--background))',
                foreground: 'hsl(var(--foreground))',
                primary: {
                    DEFAULT: 'hsl(var(--primary))',
                    // INK, not white: white on the brand red is 3.34:1 and a
                    // 14px button label is normal text. See index.css.
                    foreground: 'hsl(var(--primary-foreground))',
                    // Brand as INK. `text-primary` on a light surface is
                    // 3.34:1 — use `text-primary-emphasis` for brand-coloured
                    // text, icons and rules. See the note in index.css.
                    emphasis: 'hsl(var(--primary-emphasis))',
                },
                // Fixed identity colours, theme-independent: the logo tile's
                // RED, the INK that is the brand's third colour, and the white
                // linework inside the mark itself. Chrome and states derive
                // from the semantic tokens above, never from these.
                // `brand-ink` is the MARK's white — graphics and display type
                // on red only, never a control label.
                brand: {
                    DEFAULT: 'hsl(var(--brand))',
                    2: 'hsl(var(--brand-2))',
                    ink: 'hsl(var(--brand-ink))',
                    50: '#F5F3FF',
                    100: '#EDE9FE',
                    200: '#DDD6FE',
                    300: '#C4B5FD',
                    400: '#A78BFA',
                    500: '#8B5CF6',
                    600: '#7C3AED',
                    700: '#6D28D9',
                    800: '#5B21B6',
                    900: '#4C1D95',
                },
                fest: {
                    violet: 'hsl(var(--fest-violet))',
                    blue: 'hsl(var(--fest-blue))',
                    orange: 'hsl(var(--fest-orange))',
                    cyan: 'hsl(var(--fest-cyan))',
                    pink: 'hsl(var(--fest-pink))',
                    yellow: 'hsl(var(--fest-yellow))',
                    green: 'hsl(var(--fest-green))',
                },
                // The wash behind a modal or a drawer. `bg-scrim`, never
                // `bg-black/50` — see index.css for why a neutral black
                // scrim fails on the ink ground.
                scrim: 'hsl(var(--scrim))',
                // Ink for type and linework laid over a PHOTOGRAPH under a
                // dark gradient. Fixed in both themes on purpose: a cover
                // image is not a theme surface. Only valid over a scrim or a
                // dark gradient — see index.css.
                // Declared without alpha so `/nn` still applies:
                // `from-media-ground/90`, `text-media-ink/70`.
                media: {
                    ink: 'hsl(var(--on-media))',
                    ground: 'hsl(var(--on-media-ground))',
                },
                // The scan screen's fixed canvas, frozen in both themes.
                // Anything rendering on `.gate-surface` names these instead
                // of spelling out `text-white` / `bg-white/10`.
                gate: {
                    DEFAULT: 'hsl(var(--gate-bg))',
                    ink: 'hsl(var(--gate-ink))',
                    'ink-muted': 'hsl(var(--gate-ink-muted))',
                    line: 'hsl(var(--gate-hairline))',
                    accent: 'hsl(var(--gate-accent))',
                },
                // The three answers a gate gives. Fills only, always under
                // `text-verdict-ink`, never re-used for ordinary chrome.
                verdict: {
                    admit: 'hsl(var(--verdict-admit))',
                    reject: 'hsl(var(--verdict-reject))',
                    duplicate: 'hsl(var(--verdict-duplicate))',
                    ink: 'hsl(var(--verdict-ink))',
                },
                secondary: {
                    DEFAULT: 'hsl(var(--secondary))',
                    foreground: 'hsl(var(--secondary-foreground))',
                },
                destructive: {
                    DEFAULT: 'hsl(var(--destructive))',
                    foreground: 'hsl(var(--destructive-foreground))',
                },
                muted: {
                    DEFAULT: 'hsl(var(--muted))',
                    foreground: 'hsl(var(--muted-foreground))',
                },
                accent: {
                    DEFAULT: 'hsl(var(--accent))',
                    foreground: 'hsl(var(--accent-foreground))',
                },
                popover: {
                    DEFAULT: 'hsl(var(--popover))',
                    foreground: 'hsl(var(--popover-foreground))',
                },
                card: {
                    DEFAULT: 'hsl(var(--card))',
                    foreground: 'hsl(var(--card-foreground))',
                },
                success: {
                    DEFAULT: 'hsl(var(--success))',
                    foreground: 'hsl(var(--success-foreground))',
                },
                // Categorical analytics-chart series — fixed hue order (the
                // CVD-safety mechanism), never reassigned by rank. See
                // index.css for the validated values and validation notes.
                chart: {
                    1: 'hsl(var(--chart-1))',
                    2: 'hsl(var(--chart-2))',
                    3: 'hsl(var(--chart-3))',
                    4: 'hsl(var(--chart-4))',
                    5: 'hsl(var(--chart-5))',
                    6: 'hsl(var(--chart-6))',
                    7: 'hsl(var(--chart-7))',
                    8: 'hsl(var(--chart-8))',
                    track: 'hsl(var(--chart-track))',
                },
                warning: {
                    DEFAULT: 'hsl(var(--warning))',
                    foreground: 'hsl(var(--warning-foreground))',
                },
                sidebar: {
                    DEFAULT: 'hsl(var(--sidebar-background))',
                    foreground: 'hsl(var(--sidebar-foreground))',
                    'muted-foreground': 'hsl(var(--sidebar-muted-foreground))',
                    border: 'hsl(var(--sidebar-border))',
                    accent: 'hsl(var(--sidebar-accent))',
                    'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
                    primary: 'hsl(var(--sidebar-primary))',
                    'primary-foreground': 'hsl(var(--sidebar-primary-foreground))',
                    bg: '#0D111D',
                    hover: '#161B2E',
                    active: '#7C3AED',
                    text: '#94A3B8',
                    'admin-border': '#1E293B',
                },
            },
            borderRadius: {
                lg: `var(--radius)`,
                md: `calc(var(--radius) - 2px)`,
                sm: 'calc(var(--radius) - 4px)',
            },
            fontFamily: {
                sans: ['var(--font-sans)', ...defaultTheme.fontFamily.sans],
                display: ['var(--font-display)', ...defaultTheme.fontFamily.sans],
                accent: ['var(--font-accent)', ...defaultTheme.fontFamily.sans],
                mono: ['var(--font-mono)', ...defaultTheme.fontFamily.mono],
            },
            // Display scale for headlines/hero copy — a deliberate step up from
            // the body scale rather than just bigger body text: tighter tracking,
            // heavier weight, tuned line-height so big type doesn't feel loose.
            // Additive only — existing text-* utilities are untouched, so pages
            // using them are unaffected; this is opt-in for headline treatments.
            fontSize: {
                'display-2xl': ['4.5rem', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '800' }],
                'display-xl': ['3.5rem', { lineHeight: '1.08', letterSpacing: '-0.03em', fontWeight: '800' }],
                'display-lg': ['2.75rem', { lineHeight: '1.1', letterSpacing: '-0.025em', fontWeight: '800' }],
                'display-md': ['2.125rem', { lineHeight: '1.15', letterSpacing: '-0.02em', fontWeight: '700' }],
                'display-sm': ['1.625rem', { lineHeight: '1.2', letterSpacing: '-0.015em', fontWeight: '700' }],
            },
            // Elevation language: a restrained ramp from "resting" to "floating"
            // plus a brand-tinted glow for the rare moment something should look
            // lit-up (primary CTAs, the active scan surface) rather than merely
            // raised. Layered shadows (soft ambient + tighter key shadow) read as
            // more considered than Tailwind's single-shadow defaults.
            //
            // The three ramp steps are read from the STYLESHEET rather than
            // written here, because a shadow is a colour and colours flip with
            // the theme. These were literal `rgb(0 0 0 / 0.04)` triples: a fair
            // key light on white paper, and effectively invisible on the ink
            // ground, so in dark mode a raised card and a flat one were the same
            // object. `--shadow-*` is defined per theme in index.css, where the
            // dark ramp also adds an inset top highlight — the thing that
            // actually reads as "lifted" on a dark surface. `glow-primary`
            // stays inline: it is a brand accent, not part of the ramp, and it
            // is already token-derived.
            boxShadow: {
                soft: 'var(--shadow-soft)',
                elevated: 'var(--shadow-elevated)',
                floating: 'var(--shadow-floating)',
                // Casts upward. For a bar docked to the bottom of the
                // viewport, whose shadow falls onto the content it covers.
                docked: 'var(--shadow-docked)',
                'glow-primary': '0 0 0 1px hsl(var(--primary) / 0.4), 0 4px 24px -4px hsl(var(--primary) / 0.45)',
            },
            transitionTimingFunction: {
                emphasized: 'cubic-bezier(0.2, 0, 0, 1)',
            },
            keyframes: {
                'accordion-down': {
                    from: { height: '0' },
                    to: { height: 'var(--radix-accordion-content-height)' },
                },
                'accordion-up': {
                    from: { height: 'var(--radix-accordion-content-height)' },
                    to: { height: '0' },
                },
                'fade-in': {
                    from: { opacity: '0' },
                    to: { opacity: '1' },
                },
                'rise-in': {
                    from: { opacity: '0', transform: 'translateY(6px)' },
                    to: { opacity: '1', transform: 'translateY(0)' },
                },
                'pulse-ring': {
                    '0%': { transform: 'scale(0.9)', opacity: '0.8' },
                    '80%, 100%': { transform: 'scale(1.6)', opacity: '0' },
                },
                shimmer: {
                    '100%': { transform: 'translateX(100%)' },
                },
                'partner-marquee': {
                    from: { transform: 'translateX(0)' },
                    to: { transform: 'translateX(-50%)' },
                },
            },
            animation: {
                'accordion-down': 'accordion-down 0.2s ease-out',
                'accordion-up': 'accordion-up 0.2s ease-out',
                'fade-in': 'fade-in 0.4s ease-out',
                'rise-in': 'rise-in 0.35s cubic-bezier(0.2, 0, 0, 1)',
                'pulse-ring': 'pulse-ring 1.6s cubic-bezier(0.2,0.6,0.4,1) infinite',
                shimmer: 'shimmer 1.8s ease-in-out infinite',
                'partner-marquee': 'partner-marquee 45s linear infinite',
            },
        },
    },
    plugins: [tailwindcssAnimate, tailwindcssTypography, hitArea],
};
