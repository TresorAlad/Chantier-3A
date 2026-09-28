import { useLayoutEffect, useState } from 'react';
import { useLocation, useSearchParams } from 'react-router-dom';

const emailKey = (orderId: string) => `tdev-guest-email-${orderId}`;

export type GuestOrderLocationState = {
    email?: string;
};

/** Mémorise l'e-mail acheteur pour les pages invité (facture / billet) sans le mettre dans l'URL. */
export function rememberGuestOrderEmail(orderId: string, email: string): void {
    const normalized = email.trim();
    if (!orderId || !normalized) return;
    try {
        sessionStorage.setItem(emailKey(orderId), normalized);
    } catch {
        /* private mode */
    }
}

export function readGuestOrderEmail(orderId: string): string | null {
    try {
        return sessionStorage.getItem(emailKey(orderId))?.trim() || null;
    } catch {
        return null;
    }
}

export function resolveGuestEmail(orderId: string, fromQuery: string, fromState?: string): string {
    const state = fromState?.trim() ?? '';
    const query = fromQuery.trim();
    const session = orderId ? readGuestOrderEmail(orderId) : '';
    return state || query || session || '';
}

/**
 * Résout l'e-mail invité avant le premier paint (state React Router > query > session).
 * Évite une page vide après navigate() depuis le dialogue d'inscription.
 */
export function useGuestOrderEmail(orderId: string | undefined): string {
    const location = useLocation();
    const [searchParams] = useSearchParams();
    const stateEmail = (location.state as GuestOrderLocationState | null)?.email;
    const [email, setEmail] = useState(() =>
        orderId ? resolveGuestEmail(orderId, searchParams.get('email') ?? '', stateEmail) : '',
    );

    useLayoutEffect(() => {
        if (!orderId) {
            setEmail('');
            return;
        }
        const resolved = resolveGuestEmail(orderId, searchParams.get('email') ?? '', stateEmail);
        setEmail(resolved);
        if (resolved) {
            rememberGuestOrderEmail(orderId, resolved);
        }
    }, [orderId, searchParams, stateEmail]);

    return email;
}
