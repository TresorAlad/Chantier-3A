import { DEFAULT_FESTIVAL_CURRENCY, PASS_TIER_PRICE_MINOR } from '@/lib/festival-storefront';
import { formatMoney } from '@/lib/money';

/** Pass vendu via l'API au moment du checkout (pas au chargement de la page). */
export type BilletterieCheckoutTier = 'student' | 'vip';

/** Palette des cartes vitrine (indépendante du thème global). */
export type BilletterieCardAccent = 'festival' | 'nexus' | 'neutral';

/** Carte affichée sur la landing sans appel backend. */
export interface BilletterieListingProduct {
    listingId: string;
    title: string;
    subtitle?: string;
    priceLabel: string;
    isFree: boolean;
    description: string;
    inclusions: string[];
    category: string;
    popular: boolean;
    badgeText?: string;
    externalUrl?: string;
    checkoutTier?: BilletterieCheckoutTier;
    cardAccent?: BilletterieCardAccent;
}

export const STATIC_FESTIVAL_TITLE = 'TDEV Festival 2026';
export const STATIC_VENUE_LABEL = 'Lieu principal du festival';

/** Boutique officielle Welcome Pack / merch (vitrine + admin). */
export const WELCOME_PACK_SHOP_URL = 'https://shop.ourtdev.com';

const PASS_FESTIVAL_INCLUSIONS = [
    'Conférences tech et innovation',
    'Expositions et stands',
    'Ateliers pratiques',
    'Badge participant',
];

const NEXUS_NIGHT_INCLUSIONS = [
    'Accès complet au festival inclus',
    'Soirée jeux et gaming',
    'Cosplay manga',
    'DJ set en direct',
    'Projections exclusives',
];

/** Contenu marketing local : indépendant de la base et des migrations backend. */
export function getStaticBilletterieListing(): BilletterieListingProduct[] {
    const currency = DEFAULT_FESTIVAL_CURRENCY;
    const nexusPrice = formatMoney(PASS_TIER_PRICE_MINOR.vip, currency);

    return [
        {
            listingId: 'pass-festival',
            checkoutTier: 'student',
            title: 'Pass Festival',
            subtitle: 'Accès général',
            priceLabel: 'GRATUIT',
            isFree: true,
            description:
                'Inscription gratuite pour les conférences, ateliers et espaces du festival sur deux jours.',
            inclusions: PASS_FESTIVAL_INCLUSIONS,
            category: 'Accès général',
            popular: true,
            badgeText: 'Pass incontournable',
            cardAccent: 'festival',
        },
        {
            listingId: 'pass-nexus-night',
            checkoutTier: 'vip',
            cardAccent: 'nexus',
            title: 'Pass Nexus Night',
            subtitle: 'Soirée exclusive',
            priceLabel: nexusPrice,
            isFree: false,
            description:
                'Accès aux deux jours du festival et à la soirée Nexus Night : entertainment, gaming et ambiance festival.',
            inclusions: NEXUS_NIGHT_INCLUSIONS,
            category: 'Soirée et entertainment',
            popular: false,
            badgeText: 'Événement spécial',
        },
        {
            listingId: 'welcome-pack',
            title: 'Welcome Pack',
            subtitle: 'Pack goodies',
            priceLabel: 'Sur choix',
            isFree: false,
            description: 'Kit officiel du festival et merchandising partenaires.',
            inclusions: ['Goodies exclusifs', 'Merch édition limitée', 'Surprises partenaires'],
            category: 'Goodies et merch',
            popular: false,
            badgeText: 'Édition limitée',
            externalUrl: WELCOME_PACK_SHOP_URL,
            cardAccent: 'neutral',
        },
    ];
}

const CARD_ACCENT_CLASS: Record<BilletterieCardAccent, string> = {
    festival:
        'border-2 border-primary/35 shadow-elevated bg-gradient-to-b from-primary/12 via-white to-white',
    nexus: 'border-2 border-amber-500/45 bg-gradient-to-b from-amber-100/80 via-white to-white shadow-[0_8px_28px_-10px_rgba(245,158,11,0.35)]',
    neutral: 'border-border/70 bg-white/90 hover:border-primary/35 shadow-soft',
};

export function billetterieCardClass(ticket: BilletterieListingProduct): string {
    const accent = ticket.cardAccent ?? (ticket.isFree ? 'festival' : ticket.checkoutTier === 'vip' ? 'nexus' : 'neutral');
    const base =
        'w-full flex flex-col overflow-hidden relative transition-all duration-300 hover:shadow-floating hover:-translate-y-1';
    return `${base} ${CARD_ACCENT_CLASS[accent]}`;
}

export function billetteriePriceClass(ticket: BilletterieListingProduct): string {
    if (ticket.cardAccent === 'nexus' || ticket.checkoutTier === 'vip') {
        return 'text-amber-700';
    }
    if (ticket.isFree) {
        return 'text-primary-emphasis';
    }
    return 'text-foreground';
}

export function billetterieCtaVariant(ticket: BilletterieListingProduct): 'default' | 'outline' {
    if (ticket.cardAccent === 'nexus' || ticket.checkoutTier === 'vip') return 'default';
    return ticket.popular ? 'default' : 'outline';
}

export function billetterieCtaClass(ticket: BilletterieListingProduct): string {
    if (ticket.cardAccent === 'nexus' || ticket.checkoutTier === 'vip') {
        return 'w-full font-bold h-11 bg-amber-600 hover:bg-amber-700 text-white border-0 shadow-md';
    }
    return `w-full font-bold h-11 ${ticket.popular ? 'shadow-glow-primary' : ''}`;
}
