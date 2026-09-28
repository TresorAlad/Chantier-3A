import { DEFAULT_FESTIVAL_CURRENCY, PASS_TIER_PRICE_MINOR } from '@/lib/festival-storefront';
import { formatMoney } from '@/lib/money';

/** Pass vendu via l'API au moment du checkout (pas au chargement de la page). */
export type BilletterieCheckoutTier = 'student' | 'vip';

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
}

export const STATIC_FESTIVAL_TITLE = 'TDEV Festival 2026';
export const STATIC_VENUE_LABEL = 'Lieu principal du festival';

const PASS_FESTIVAL_INCLUSIONS = [
    'Conférences tech et innovation',
    'Expositions et stands',
    'Ateliers pratiques',
    'Badge participant',
];

const NEXUS_NIGHT_INCLUSIONS = [
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
        },
        {
            listingId: 'pass-nexus-night',
            checkoutTier: 'vip',
            title: 'Pass Nexus Night',
            subtitle: 'Soirée exclusive',
            priceLabel: nexusPrice,
            isFree: false,
            description: 'Accès à la soirée Nexus Night : entertainment, gaming et ambiance festival.',
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
            externalUrl: 'https://shop.tdevfestival.com',
        },
    ];
}
