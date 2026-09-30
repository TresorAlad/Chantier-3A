import { ApiError } from '@/lib/api';

const DEV_HINT_PATTERN = /backend-python|VITE_DEV_API_PROXY|8088|Démarrez/i;

export interface CheckoutFailureCopy {
    title: string;
    body: string;
}

/** Messages visiteur pour les popups d'échec (sans instructions dev). */
export function checkoutFailureCopy(err: unknown): CheckoutFailureCopy {
    if (err instanceof ApiError) {
        if (err.code === 'duplicate_registration') {
            return {
                title: 'Inscription déjà enregistrée',
                body:
                    err.message.trim() ||
                    'Cette adresse e-mail a déjà été utilisée pour une inscription à cet événement.',
            };
        }

        const infra =
            err.code === 'network_error' ||
            err.status === 0 ||
            err.status >= 500 ||
            DEV_HINT_PATTERN.test(err.message);

        if (err.code === 'ticketing_unavailable') {
            return {
                title: 'Billet en cours d\'émission',
                body:
                    err.message.trim() ||
                    'Votre paiement a été enregistré. L\'émission du billet prend plus de temps que prévu : consultez vos e-mails ou réessayez le téléchargement dans quelques minutes.',
            };
        }

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
