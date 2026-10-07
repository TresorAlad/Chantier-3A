import {
  getStaticBilletterieListing,
  type BilletterieCheckoutTier,
  type BilletterieListingProduct,
} from '@/lib/static-billetterie-catalog';

/** Segments d’URL publics à communiquer à l’équipe landing externe. */
export const INSCRIPTION_PATHS = {
  passFestival: '/inscription/pass-festival',
  nexusNight: '/inscription/nexus-night',
} as const;

const SLUG_TO_TIER: Record<string, BilletterieCheckoutTier> = {
  'pass-festival': 'student',
  festival: 'student',
  gratuit: 'student',
  free: 'student',
  student: 'student',
  'nexus-night': 'vip',
  nexus: 'vip',
  vip: 'vip',
  payant: 'vip',
};

export function tierFromSlug(slug: string): BilletterieCheckoutTier | null {
  const key = slug.trim().toLowerCase();
  return SLUG_TO_TIER[key] ?? null;
}

export function listingForTier(tier: BilletterieCheckoutTier): BilletterieListingProduct | null {
  return getStaticBilletterieListing().find((p) => p.checkoutTier === tier) ?? null;
}

export function resolveInscriptionListing(
  pathname: string,
  searchParams: URLSearchParams,
): BilletterieListingProduct | null {
  const segments = pathname.split('/').filter(Boolean);
  const last = segments[segments.length - 1]?.toLowerCase() ?? '';
  if (segments[0] === 'inscription' && last && last !== 'inscription') {
    const tier = tierFromSlug(last);
    if (tier) return listingForTier(tier);
  }

  const passParam = searchParams.get('pass') ?? searchParams.get('tier') ?? '';
  const tierFromQuery = tierFromSlug(passParam);
  if (tierFromQuery) return listingForTier(tierFromQuery);

  return null;
}

export function isEmbedMode(searchParams: URLSearchParams): boolean {
  const v = (searchParams.get('embed') ?? searchParams.get('popup') ?? '').toLowerCase();
  return v === '1' || v === 'true' || v === 'yes';
}

/** Couleur d’accent partenaire (#RRGGBB ou RRGGBB) pour harmoniser le formulaire en embed. */
export function applyPartnerAccentFromQuery(searchParams: URLSearchParams): void {
  const raw = (searchParams.get('accent') ?? searchParams.get('primary') ?? '').trim();
  const hex = raw.replace(/^#/, '');
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return;

  const r = parseInt(hex.slice(0, 2), 16) / 255;
  const g = parseInt(hex.slice(2, 4), 16) / 255;
  const b = parseInt(hex.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      default:
        h = ((r - g) / d + 4) / 6;
    }
  }
  const root = document.documentElement;
  root.style.setProperty('--primary', `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`);
  root.style.setProperty('--primary-emphasis', `${Math.round(h * 360)} ${Math.round(Math.min(100, s * 100 + 10))}% ${Math.round(Math.max(25, l * 100 - 12))}%`);
}

export function notifyEmbedParent(
  type: 'tdev-inscription-success' | 'tdev-inscription-close',
  payload: Record<string, string>,
  parentOrigin: string | null,
): void {
  if (window.parent === window) return;
  const target = parentOrigin && parentOrigin.startsWith('http') ? parentOrigin : '*';
  window.parent.postMessage({ source: 'tdev-billetterie', type, ...payload }, target);
}
