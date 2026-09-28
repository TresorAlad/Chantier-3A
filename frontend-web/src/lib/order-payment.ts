import { buildFedapayCheckoutUrl } from '@/lib/payment-checkout';
import type { Order } from '@/lib/api-types';

const storageKey = (orderId: string) => `tdev-order-payment-${orderId}`;

export interface StoredOrderPayment {
    redirectUrl?: string;
    instructions?: string;
}

export function stashOrderPayment(orderId: string, data: StoredOrderPayment): void {
    try {
        sessionStorage.setItem(storageKey(orderId), JSON.stringify(data));
    } catch {
        /* quota / private mode */
    }
}

export function readOrderPayment(orderId: string): StoredOrderPayment | null {
    try {
        const raw = sessionStorage.getItem(storageKey(orderId));
        if (!raw) return null;
        return JSON.parse(raw) as StoredOrderPayment;
    } catch {
        return null;
    }
}

export function clearOrderPayment(orderId: string): void {
    try {
        sessionStorage.removeItem(storageKey(orderId));
    } catch {
        /* ignore */
    }
}

/** URL FedaPay (API ou VITE_FEDAPAY_CHECKOUT_URL) enregistrée à la création de commande. */
export function resolvePassCheckoutUrl(order: Order, stored: StoredOrderPayment | null): string | null {
    const fromCreate = stored?.redirectUrl?.trim();
    if (fromCreate) return fromCreate;
    if (order.total_minor <= 0) return null;
    return buildFedapayCheckoutUrl({
        orderId: order.id,
        amountMinor: order.total_minor,
        currency: order.currency,
        email: order.buyer_email,
        name: order.buyer_name,
    });
}
