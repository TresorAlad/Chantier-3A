import { orders as ordersApi, payments as paymentsApi } from '@/lib/api';
import { payWithFedapay } from '@/lib/fedapay-checkout';
import type { TicketType } from '@/lib/api-types';
import {
    toRegistrationFormPayload,
    labelsForChoices,
    PARTICIPATION_REASON_OPTIONS,
    type RegistrationFormValues,
} from '@/lib/registration-form';

export type CheckoutOutcome =
    | { kind: 'free_confirmed'; orderId: string; email: string }
    | { kind: 'paid'; orderId: string; email: string }
    | { kind: 'paid_pending'; orderId: string; email: string; redirectUrl?: string };

export async function completeCheckout(params: {
    eventId: string;
    ticketType: TicketType;
    registration: RegistrationFormValues;
    /** Appelé juste avant l'ouverture du widget : l'appelant doit fermer ses modales (voir fedapay-checkout.ts). */
    onPaymentStart?: () => void;
}): Promise<CheckoutOutcome> {
    const { eventId, ticketType, registration, onPaymentStart } = params;
    const form = toRegistrationFormPayload(registration);
    const first = form.first_name;
    const last = form.last_name;
    const email = form.email;
    const name = `${first} ${last}`.trim();

    const result = await ordersApi.create({
        event_id: eventId,
        items: [{ ticket_type_id: ticketType.id, quantity: 1 }],
        buyer: {
            email,
            first_name: first,
            last_name: last,
            name,
            motivation: labelsForChoices(PARTICIPATION_REASON_OPTIONS, form.participation_reasons).join(', '),
            wish: form.expectations,
            school_name: form.school_program,
            form,
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
