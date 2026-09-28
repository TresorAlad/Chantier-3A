/**
 * Variables d'environnement Vite (préfixe VITE_).
 * Tout ce qui passe par import.meta.env est inclus dans le bundle client :
 * ne jamais y mettre de secrets (clés API privées, mots de passe, tokens).
 */

const DEFAULT_ADMIN_ROUTE = '/acces-admin-billetterie';

/** Chemin interne de la page admin (obscurité, pas un secret). */
export function getAdminRoute(): string {
    const raw = import.meta.env.VITE_ADMIN_ROUTE?.trim();
    if (!raw) return DEFAULT_ADMIN_ROUTE;
    if (raw.includes('..') || !/^\/[\w/-]+$/.test(raw)) {
        return DEFAULT_ADMIN_ROUTE;
    }
    const normalized = raw.replace(/\/+$/, '');
    return normalized || DEFAULT_ADMIN_ROUTE;
}

export function getFestivalEventSlug(): string | undefined {
    const slug = import.meta.env.VITE_FESTIVAL_EVENT_SLUG?.trim();
    return slug || undefined;
}

export function getOptionalEnv(key: keyof ImportMetaEnv): string | undefined {
    const raw = import.meta.env[key];
    if (typeof raw !== 'string') return undefined;
    const trimmed = raw.trim();
    return trimmed.length > 0 ? trimmed : undefined;
}

/** URL HTTPS externe uniquement (paiement public, réseaux sociaux). */
export function getOptionalHttpsUrl(key: keyof ImportMetaEnv): string | undefined {
    const value = getOptionalEnv(key);
    if (!value) return undefined;
    try {
        const url = new URL(value);
        if (url.protocol !== 'https:' && url.protocol !== 'http:') return undefined;
        return url.toString();
    } catch {
        return undefined;
    }
}
