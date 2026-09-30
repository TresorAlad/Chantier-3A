import { ApiError } from '@/lib/api';

const DEV_HINT_PATTERN = /backend-python|VITE_DEV_API_PROXY|8088|Démarrez/i;

const TECHNICAL_MESSAGE_PATTERN =
    /internal|http_\d|request failed|network error|check your connection|unauthorized|forbidden|not found|event not found|provider not|postgresql|database|vault|fedapay|smtp|api\/|render|vercel|neon|misconfigured|reference is required/i;

export interface CheckoutFailureCopy {
    title: string;
    body: string;
}

const GENERIC_UNAVAILABLE: CheckoutFailureCopy = {
    title: 'Billetterie indisponible',
    body: 'Nous ne pouvons pas traiter votre réservation pour le moment. Veuillez réessayer dans quelques instants.',
};

const GENERIC_RESERVATION: CheckoutFailureCopy = {
    title: 'Échec de la réservation',
    body: 'Une erreur est survenue. Veuillez réessayer.',
};

function looksLikeVisitorFrench(text: string): boolean {
    const t = text.trim();
    if (!t || t.length > 320) return false;
    if (TECHNICAL_MESSAGE_PATTERN.test(t)) return false;
    if (/^[A-Za-z0-9\s._\-:'",!?()]+$/.test(t) && !/[àâäéèêëïîôùûüç]/i.test(t)) {
        return false;
    }
    return true;
}

/** Détails techniques : console uniquement, jamais dans les modales visiteur. */
export function logCheckoutDiagnostic(context: string, err: unknown): void {
    if (err instanceof ApiError) {
        console.error(`[billetterie:${context}]`, {
            code: err.code,
            status: err.status,
            message: err.message,
            cause: err.cause,
        });
        return;
    }
    console.error(`[billetterie:${context}]`, err);
}

/** Messages visiteur pour les popups d'échec (sans jargon technique). */
export function checkoutFailureCopy(err: unknown): CheckoutFailureCopy {
    if (err instanceof ApiError) {
        if (err.code === 'duplicate_registration') {
            const msg = err.message.trim();
            return {
                title: 'Inscription déjà enregistrée',
                body:
                    (looksLikeVisitorFrench(msg) && msg) ||
                    'Cette adresse e-mail a déjà été utilisée pour une inscription à cet événement.',
            };
        }

        if (err.code === 'database_unavailable' || err.code === 'network_error') {
            return GENERIC_UNAVAILABLE;
        }

        if (err.code === 'ticketing_unavailable') {
            return {
                title: 'Billet en cours d\'émission',
                body:
                    'Votre paiement est enregistré. Votre billet arrive par e-mail sous peu ; vous pouvez aussi réessayer le téléchargement dans quelques minutes.',
            };
        }

        if (err.code === 'not_found' || err.status === 404) {
            return {
                title: 'Événement indisponible',
                body: 'Les inscriptions ne sont pas ouvertes pour le moment. Revenez un peu plus tard.',
            };
        }

        const infra =
            err.status === 0 ||
            err.status >= 500 ||
            err.code.startsWith('http_5') ||
            DEV_HINT_PATTERN.test(err.message);

        if (infra) {
            return GENERIC_UNAVAILABLE;
        }

        if (err.status === 400 && err.code === 'invalid_request') {
            const msg = err.message.trim();
            if (looksLikeVisitorFrench(msg)) {
                return { title: 'Échec de la réservation', body: msg };
            }
            return GENERIC_RESERVATION;
        }

        const msg = err.message.trim();
        if (looksLikeVisitorFrench(msg)) {
            return { title: 'Échec de la réservation', body: msg };
        }

        return GENERIC_RESERVATION;
    }

    if (err instanceof Error && err.message.trim()) {
        if (DEV_HINT_PATTERN.test(err.message) || TECHNICAL_MESSAGE_PATTERN.test(err.message)) {
            return GENERIC_UNAVAILABLE;
        }
        const msg = err.message.trim();
        if (looksLikeVisitorFrench(msg)) {
            return { title: 'Échec de la réservation', body: msg };
        }
        return GENERIC_RESERVATION;
    }

    return GENERIC_RESERVATION;
}
