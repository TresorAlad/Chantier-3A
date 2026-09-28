import { orders as ordersApi, payments as paymentsApi } from '@/lib/api';
import { stashOrderPayment } from '@/lib/order-payment';
import type { FestivalEvent, TicketType } from '@/lib/api-types';
import type { PassTierId } from '@/lib/festival-storefront';
import { isPaidPassTier } from '@/lib/festival-storefront';

export interface PassRegistrationInput {
    first_name: string;
    last_name: string;
    email: string;
    school_name?: string;
    motivation?: string;
    wish: string;
}

export type PassCheckoutResult =
    | { kind: 'free_confirmed'; orderId: string; email: string }
    | { kind: 'invoice'; orderId: string; email: string };

const looksLikeEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

export function validatePassRegistration(
    tier: PassTierId,
    input: PassRegistrationInput,
): Partial<Record<keyof PassRegistrationInput, string>> {
    const errors: Partial<Record<keyof PassRegistrationInput, string>> = {};
    if (!input.first_name.trim()) errors.first_name = 'Indiquez votre prénom.';
    if (!input.last_name.trim()) errors.last_name = 'Indiquez votre nom.';
    if (!input.email.trim()) errors.email = 'Indiquez votre e-mail.';
    else if (!looksLikeEmail(input.email)) errors.email = 'Adresse e-mail invalide.';
    if (!input.wish.trim()) errors.wish = 'Partagez vos attentes pour l\'édition 2026.';
    if (tier === 'student') {
        if (!input.school_name?.trim()) {
            errors.school_name = 'Indiquez le nom de votre école ou établissement.';
        }
        if (!input.motivation?.trim()) {
            errors.motivation = 'Expliquez pourquoi vous souhaitez participer.';
        }
    }
    return errors;
}

export async function completePassPurchase(params: {
    event: FestivalEvent;
    ticketType: TicketType;
    tier: PassTierId;
    registration: PassRegistrationInput;
}): Promise<PassCheckoutResult> {
    const { event, ticketType, tier, registration } = params;
    const first = registration.first_name.trim();
    const last = registration.last_name.trim();
    const email = registration.email.trim();
    const wish = registration.wish.trim();
    const name = `${first} ${last}`.trim();

    const buyer =
        tier === 'student'
            ? {
                  email,
                  first_name: first,
                  last_name: last,
                  wish,
                  school_name: registration.school_name?.trim() ?? '',
                  motivation: registration.motivation?.trim() ?? '',
                  name,
              }
            : {
                  email,
                  first_name: first,
                  last_name: last,
                  wish,
                  name,
              };

    const result = await ordersApi.create({
        event_id: event.id,
        items: [{ ticket_type_id: ticketType.id, quantity: 1 }],
        buyer,
    });

    const order = result.order;

    if (isPaidPassTier(tier)) {
        const redirect = result.payment?.redirect_url?.trim();
        if (redirect) {
            stashOrderPayment(order.id, { redirectUrl: redirect });
        }
        return { kind: 'invoice', orderId: order.id, email };
    }

    try {
        await paymentsApi.verify(order.id);
    } catch {
        /* Pass gratuit : peut déjà être réglé côté serveur */
    }
    return { kind: 'free_confirmed', orderId: order.id, email };
}
