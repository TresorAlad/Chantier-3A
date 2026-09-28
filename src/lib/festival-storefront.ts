import type { FestivalEvent, TicketType } from '@/lib/api-types';
import { productKindOf, remainingFor, visibleTicketTypes } from '@/lib/ticket-utils';

export const PASS_TIER_ORDER = ['student', 'standard', 'vip'] as const;
export type PassTierId = (typeof PASS_TIER_ORDER)[number];

export const PASS_TIER_LABELS: Record<PassTierId, string> = {
    student: 'Pass étudiant',
    standard: 'Pass standard',
    vip: 'Pass VIP',
};

export interface PassTierCatalogEntry {
    id: string;
    label: string;
    available: boolean;
    price_minor?: number;
}

export const PASS_TIER_PRICE_MINOR: Record<PassTierId, number> = {
    student: 0,
    standard: 2000,
    vip: 5000,
};

/** Fallback when GET /api/pass-tiers is unreachable (dev sans API). */
export function defaultPassTierCatalog(): PassTierCatalogEntry[] {
    return PASS_TIER_ORDER.map((tier) => ({
        id: tier,
        label: PASS_TIER_LABELS[tier],
        available: true,
        price_minor: PASS_TIER_PRICE_MINOR[tier],
    }));
}

export interface PassOffer {
    tier: PassTierId;
    label: string;
    ticketType: TicketType | null;
    /** Tier is enabled for sale in GET /api/pass-tiers. */
    tierEnabled: boolean;
    purchasable: boolean;
    /** Display price from ticket type or catalog fallback. */
    priceMinor: number;
}

export function ticketTypePassTier(ticketType: TicketType): PassTierId | null {
    const raw = (ticketType as TicketType & { pass_tier?: string }).pass_tier?.trim().toLowerCase();
    if (raw === 'student' || raw === 'standard' || raw === 'vip') return raw;
    return null;
}

export function passesFromTicketTypes(ticketTypes: TicketType[], catalog: PassTierCatalogEntry[]): PassOffer[] {
    const catalogById = new Map(catalog.map((e) => [e.id, e]));
    const enabled = new Set(catalog.filter((e) => e.available).map((e) => e.id));
    const tickets = visibleTicketTypes(ticketTypes).filter((t) => productKindOf(t) === 'ticket');

    return PASS_TIER_ORDER.map((tier) => {
        const ticketType = tickets.find((t) => ticketTypePassTier(t) === tier) ?? null;
        const tierEnabled = enabled.has(tier);
        const catalogPrice = catalogById.get(tier)?.price_minor ?? PASS_TIER_PRICE_MINOR[tier];
        const priceMinor = ticketType?.price_minor ?? catalogPrice;
        const purchasable = Boolean(ticketType && tierEnabled && remainingFor(ticketType) > 0);
        return {
            tier,
            label: PASS_TIER_LABELS[tier],
            ticketType,
            tierEnabled,
            purchasable,
            priceMinor,
        };
    });
}

export function isPaidPassTier(tier: PassTierId): boolean {
    return tier === 'standard' || tier === 'vip';
}

export function goodiesFromTicketTypes(ticketTypes: TicketType[]): TicketType[] {
    return visibleTicketTypes(ticketTypes).filter((t) => productKindOf(t) === 'goodie');
}

export function cartNeedsStudentRegistration(items: { ticket_type: TicketType }[]): boolean {
    return items.some((i) => productKindOf(i.ticket_type) === 'ticket' && ticketTypePassTier(i.ticket_type) === 'student');
}

export function cartNeedsPaidPassRegistration(items: { ticket_type: TicketType }[]): boolean {
    return items.some((i) => {
        const tier = ticketTypePassTier(i.ticket_type);
        return productKindOf(i.ticket_type) === 'ticket' && (tier === 'standard' || tier === 'vip');
    });
}

export function resolveFestivalEventSlug(envSlug: string | undefined, events: FestivalEvent[]): string | null {
    const configured = envSlug?.trim();
    if (configured) return configured;
    const published = events.find((e) => e.status === 'published') ?? events[0];
    return published?.slug || published?.id || null;
}

export const DEFAULT_FESTIVAL_CURRENCY = 'XOF';
