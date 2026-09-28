import { clsx, type ClassValue } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

// tailwind-merge ships a fixed idea of which suffixes belong to which class
// group (e.g. "shadow" only knows "", "inner", "none", a t-shirt-size
// matcher and an arbitrary-value matcher). It does NOT read
// `tailwind.config.js`, so a custom key added there under `theme.extend` —
// `boxShadow.soft`, `fontSize['display-lg']`, `transitionTimingFunction.
// emphasized`, `animation['fade-in']` — is invisible to it. Without this,
// `cn('shadow-soft', 'shadow-none')` keeps BOTH classes (they don't look
// like the same group), and CSS source order — not the later class in the
// call — decides which one paints. That was a real, silent bug: a page
// passing `shadow-none` to override `Input`'s `shadow-soft` was a no-op,
// because Tailwind emits the base "none" step before this file's custom
// "soft" step, so "soft" always wins regardless of class order.
//
// Registering the same custom keys here (as plain suffixes, matching
// `tailwind.config.js`'s `theme.extend` exactly) teaches tailwind-merge
// that they conflict with their built-in siblings, so the LAST class in a
// `cn(...)` call wins again, as every caller assumes it does.
//
// Keep this list in lockstep with `tailwind.config.js`'s `extend` block: a
// new custom `boxShadow`/`fontSize`/`transitionTimingFunction`/`animation`
// key that isn't added here reintroduces exactly this bug for that key.
const twMerge = extendTailwindMerge({
    classGroups: {
        shadow: [{ shadow: ['soft', 'elevated', 'floating', 'docked', 'glow-primary'] }],
        'font-size': [{ text: ['display-2xl', 'display-xl', 'display-lg', 'display-md', 'display-sm'] }],
        ease: [{ ease: ['emphasized'] }],
        animate: [{ animate: ['accordion-down', 'accordion-up', 'fade-in', 'rise-in', 'pulse-ring', 'shimmer'] }],
    },
});

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * A v4 UUID that works outside secure contexts.
 *
 * `crypto.randomUUID()` is gated behind secure contexts (https, or
 * localhost). Tdev Festival's gate scanner is explicitly meant to run on a phone
 * on a local venue network, which may well be plain HTTP — so we can't rely
 * on it. `crypto.getRandomValues` has no such restriction, so build a v4 UUID
 * from it by hand; only fall back to Math.random if even that is missing.
 */
export function uuid() {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
        try {
            return crypto.randomUUID();
        } catch {
            // secure-context check failed — fall through to the manual path
        }
    }

    const bytes = new Uint8Array(16);
    if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
        crypto.getRandomValues(bytes);
    } else {
        for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
    }

    // Indices 6 and 8 are always in range: `bytes` was just allocated at
    // length 16 above, two lines up, and never resized.
    bytes[6] = ((bytes[6] as number) & 0x0f) | 0x40; // version 4
    bytes[8] = ((bytes[8] as number) & 0x3f) | 0x80; // variant 10

    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
