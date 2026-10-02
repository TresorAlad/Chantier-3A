/**
 * Variables d'environnement Vite (préfixe VITE_).
 * Tout ce qui passe par import.meta.env est inclus dans le bundle client :
 * ne jamais y mettre de secrets (clés API privées, mots de passe, tokens).
 */

const MIN_ADMIN_ROUTE_LEN = 12;

function normalizeAdminRoute(raw: string): string | null {
    const trimmed = raw.trim();
    if (!trimmed || trimmed.includes('..') || !/^\/[\w/-]+$/.test(trimmed)) {
        return null;
    }
    const normalized = trimmed.replace(/\/+$/, '');
    if (!normalized || normalized.length < MIN_ADMIN_ROUTE_LEN) {
        return null;
    }
    return normalized;
}

/** Chemin interne du dashboard admin (obscurité, pas un secret). Absent = admin désactivé. */
export function getAdminRoute(): string | null {
    const raw = import.meta.env.VITE_ADMIN_ROUTE?.trim();
    if (!raw) {
        if (import.meta.env.DEV) {
            console.warn(
                '[billetterie] VITE_ADMIN_ROUTE manquant : le dashboard admin n’est pas monté.',
            );
        }
        return null;
    }
    const route = normalizeAdminRoute(raw);
    if (!route) {
        if (import.meta.env.DEV) {
            console.warn(
                '[billetterie] VITE_ADMIN_ROUTE invalide ou trop court (min. 12 caractères).',
            );
        }
        return null;
    }
    return route;
}

export function isAdminEnabled(): boolean {
    return getAdminRoute() !== null;
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
