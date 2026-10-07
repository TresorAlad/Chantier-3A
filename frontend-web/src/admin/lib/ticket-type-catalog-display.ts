import { getStaticBilletterieListing } from '@/lib/static-billetterie-catalog';
import type { TicketType } from '../types';

export interface TicketTypeGauge {
  soldLabel: string;
  percentLabel: string;
  barWidth: number;
  remainingLabel: string;
  unlimitedQuota: boolean;
}

export interface TicketTypeDisplay {
  ticket: TicketType;
  displayTitle: string;
  displayDescription: string;
  categoryLabel: string;
  gauge: TicketTypeGauge;
}

const TIER_SORT: Record<string, number> = {
  student: 0,
  vip: 1,
  standard: 2,
};

function vitrineCopy(tier: string | undefined | null): {
  title?: string;
  description?: string;
  category?: string;
} {
  const listings = getStaticBilletterieListing();
  if (tier === 'student') {
    const item = listings.find((l) => l.checkoutTier === 'student');
    return { title: item?.title, description: item?.description, category: item?.category };
  }
  if (tier === 'vip') {
    const item = listings.find((l) => l.checkoutTier === 'vip');
    return { title: item?.title, description: item?.description, category: item?.category };
  }
  const welcome = listings.find((l) => l.listingId === 'welcome-pack');
  if (tier === 'goodie') {
    return {
      title: welcome?.title,
      description: welcome?.description,
      category: welcome?.category,
    };
  }
  return {};
}

export function computeTicketTypeGauge(tt: TicketType): TicketTypeGauge {
  const sold = tt.quantity_sold ?? 0;
  const total = tt.quantity_total ?? 0;

  if (total <= 0) {
    return {
      soldLabel: sold.toLocaleString('fr-FR'),
      percentLabel: 'Places illimitées',
      barWidth: sold > 0 ? 100 : 0,
      remainingLabel: 'Illimité',
      unlimitedQuota: true,
    };
  }

  const remaining = Math.max(0, total - sold);
  const percent = Math.min(100, Math.round((sold / total) * 100));

  return {
    soldLabel: `${sold.toLocaleString('fr-FR')} / ${total.toLocaleString('fr-FR')}`,
    percentLabel: `${percent} %`,
    barWidth: percent,
    remainingLabel: remaining.toLocaleString('fr-FR'),
    unlimitedQuota: false,
  };
}

export function buildTicketTypeDisplay(tt: TicketType): TicketTypeDisplay {
  const tier = (tt.pass_tier ?? '').toLowerCase();
  const kind = tt.product_kind === 'goodie' ? 'goodie' : tier;
  const vitrine = vitrineCopy(kind || null);

  return {
    ticket: tt,
    displayTitle: vitrine.title ?? tt.name,
    displayDescription: vitrine.description ?? tt.description ?? 'Aucune description saisie.',
    categoryLabel: vitrine.category ?? (tt.product_kind === 'goodie' ? 'Goodies et merch' : 'Billetterie'),
    gauge: computeTicketTypeGauge(tt),
  };
}

function isPublicCatalogTicket(tt: TicketType): boolean {
  const tier = (tt.pass_tier ?? '').toLowerCase();
  if (tt.product_kind === 'goodie') return true;
  return tier === 'student' || tier === 'vip';
}

export function sortTicketTypesForCatalog(types: TicketType[]): TicketType[] {
  return [...types].sort((a, b) => {
    const ta = TIER_SORT[(a.pass_tier ?? '').toLowerCase()] ?? 99;
    const tb = TIER_SORT[(b.pass_tier ?? '').toLowerCase()] ?? 99;
    if (ta !== tb) return ta - tb;
    return a.sort_order - b.sort_order;
  });
}

export function formatCatalogTicketTypes(types: TicketType[]): TicketTypeDisplay[] {
  return sortTicketTypesForCatalog(types)
    .filter(isPublicCatalogTicket)
    .map(buildTicketTypeDisplay);
}
