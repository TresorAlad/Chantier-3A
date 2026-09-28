import { getOptionalHttpsUrl } from '@/lib/env';

/**
 * Fallback checkout URL when the API does not yet return payment.redirect_url
 * (FedaPay microservice en cours de branchement). Configure at build time:
 * VITE_FEDAPAY_CHECKOUT_URL=https://pay.example/checkout
 */
export function buildFedapayCheckoutUrl(input: {
    orderId: string;
    amountMinor: number;
    currency: string;
    email: string;
    name?: string;
}): string | null {
    const base = getOptionalHttpsUrl('VITE_FEDAPAY_CHECKOUT_URL');
    if (!base) return null;
    try {
        const url = new URL(base);
        url.searchParams.set('reference', input.orderId);
        url.searchParams.set('amount', String(input.amountMinor));
        url.searchParams.set('currency', input.currency);
        url.searchParams.set('email', input.email);
        if (input.name?.trim()) url.searchParams.set('name', input.name.trim());
        return url.toString();
    } catch {
        return null;
    }
}
