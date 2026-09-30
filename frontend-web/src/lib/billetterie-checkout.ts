import { orders as ordersApi, payments as paymentsApi } from '@/lib/api';
import { payWithFedapay } from '@/lib/fedapay-checkout';
import type { TicketType } from '@/lib/api-types';

export interface RegistrationInput {
    first_name: string;
    last_name: string;
    email: string;
    motivation: string;
    wish: string;
    school_name?: string;
}

export type CheckoutOutcome =
    | { kind: 'free_confirmed'; orderId: string; email: string }
    | { kind: 'paid'; orderId: string; email: string }
    | { kind: 'paid_pending'; orderId: string; email: string; redirectUrl?: string };

const emailOk = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

function validateRegistrationFields(
    input: RegistrationInput,
    requireSchool: boolean,
): Partial<Record<keyof RegistrationInput, string>> {
    const errors: Partial<Record<keyof RegistrationInput, string>> = {};
    if (!input.first_name.trim()) errors.first_name = 'Indiquez votre prénom.';
    if (!input.last_name.trim()) errors.last_name = 'Indiquez votre nom.';
    if (!input.email.trim()) errors.email = 'Indiquez votre e-mail.';
    else if (!emailOk(input.email)) errors.email = 'Adresse e-mail invalide.';
    if (!input.motivation.trim()) errors.motivation = 'Ce champ est requis.';
    if (!input.wish.trim()) errors.wish = 'Ce champ est requis.';
    if (requireSchool && !input.school_name?.trim()) {
        errors.school_name = 'Indiquez votre école ou organisation.';
    }
    return errors;
}

export function validateRegistration(
    input: RegistrationInput,
    ticketType: TicketType,
): Partial<Record<keyof RegistrationInput, string>> {
    return validateRegistrationFields(input, ticketType.pass_tier === 'student');
}

/** Validation côté formulaire avant appel API (catalogue statique). */
export function validateRegistrationForCheckoutTier(
    input: RegistrationInput,
    tier: 'student' | 'vip',
): Partial<Record<keyof RegistrationInput, string>> {
    return validateRegistrationFields(input, tier === 'student');
}

export async function completeCheckout(params: {
    eventId: string;
    ticketType: TicketType;
    registration: RegistrationInput;
    /** Appelé juste avant l'ouverture du widget : l'appelant doit fermer ses modales (voir fedapay-checkout.ts). */
    onPaymentStart?: () => void;
}): Promise<CheckoutOutcome> {
    const { eventId, ticketType, registration, onPaymentStart } = params;
    const first = registration.first_name.trim();
    const last = registration.last_name.trim();
    const email = registration.email.trim();
    const name = `${first} ${last}`.trim();

    const result = await ordersApi.create({
        event_id: eventId,
        items: [{ ticket_type_id: ticketType.id, quantity: 1 }],
        buyer: {
            email,
            first_name: first,
            last_name: last,
            name,
            motivation: registration.motivation.trim(),
            wish: registration.wish.trim(),
            school_name: registration.school_name?.trim() ?? '',
        },
    });

    const order = result.order;
    const paid = ticketType.price_minor > 0;

    if (paid) {
        const transactionId = result.payment?.client_token?.trim();
        if (transactionId) {
            onPaymentStart?.();
            const outcome = await payWithFedapay({
                orderId: order.id,
                transactionId,
                customer: { email, firstname: first, lastname: last },
            });
            if (outcome === 'paid') return { kind: 'paid', orderId: order.id, email };
            return { kind: 'paid_pending', orderId: order.id, email };
        }
        const redirectUrl = result.payment?.redirect_url?.trim();
        if (redirectUrl) {
            return { kind: 'paid_pending', orderId: order.id, email, redirectUrl };
        }
        return { kind: 'paid_pending', orderId: order.id, email };
    }

    try {
        await paymentsApi.verify(order.id);
    } catch {
        /* Déjà réglé côté serveur pour les commandes gratuites */
    }
    return { kind: 'free_confirmed', orderId: order.id, email };
}
