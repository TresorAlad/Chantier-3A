import type { TicketType } from '@/lib/api-types';

export function visibleTicketTypes(ticketTypes: TicketType[] = []): TicketType[] {
    return ticketTypes.filter((t) => t.status !== 'hidden');
}

export type ProductKind = 'ticket' | 'goodie' | 'option';

export function productKindOf(ticketType: TicketType): ProductKind {
    const k = ticketType.product_kind;
    if (k === 'goodie' || k === 'option') return k;
    return 'ticket';
}

export function remainingFor(ticketType: TicketType): number {
    const total = ticketType.quantity_total ?? 0;
    const sold = ticketType.quantity_sold ?? 0;
    if (total <= 0) return Number.MAX_SAFE_INTEGER;
    return Math.max(0, total - sold);
}
