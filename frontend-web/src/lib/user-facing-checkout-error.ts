import { ApiError } from '@/lib/api';

const DEV_HINT_PATTERN = /backend-python|VITE_DEV_API_PROXY|8088|Démarrez/i;

export interface CheckoutFailureCopy {
    title: string;
    body: string;
}

/** Messages visiteur pour les popups d'échec (sans instructions dev). */
export function checkoutFailureCopy(err: unknown): CheckoutFailureCopy {
    if (err instanceof ApiError) {
        const infra =
            err.code === 'network_error' ||
            err.status === 0 ||
            err.status >= 500 ||
            DEV_HINT_PATTERN.test(err.message);

        if (infra) {
            return {
                title: 'Billetterie indisponible',
                body: 'Nous ne pouvons pas traiter votre réservation pour le moment. Veuillez réessayer dans quelques instants.',
            };
        }

        return {
            title: 'Échec de la réservation',
            body: err.message.trim() || 'Une erreur est survenue. Veuillez réessayer.',
        };
    }

    if (err instanceof Error && err.message.trim()) {
        if (DEV_HINT_PATTERN.test(err.message)) {
            return {
                title: 'Billetterie indisponible',
                body: 'Nous ne pouvons pas traiter votre réservation pour le moment. Veuillez réessayer dans quelques instants.',
            };
        }
        return {
            title: 'Échec de la réservation',
            body: err.message.trim(),
        };
    }

    return {
        title: 'Échec de la réservation',
        body: 'Une erreur est survenue. Veuillez réessayer.',
    };
}
