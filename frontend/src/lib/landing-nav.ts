/** Ancres de la page d'accueil vitrine Tdev Festival. */
export const LANDING_SECTION_IDS = [
    'edition',
    'participation',
    'moments',
    'passes',
    'goodies',
    'partenaires',
    'faq',
] as const;

export type LandingSectionId = (typeof LANDING_SECTION_IDS)[number];

export function landingSectionHash(id: LandingSectionId): `#${LandingSectionId}` {
    return `#${id}`;
}

/** Cible React Router pour une section de la landing. */
export function landingSectionTo(id: LandingSectionId) {
    return { pathname: '/', hash: landingSectionHash(id) } as const;
}

export function scrollToLandingSection(id: string, behavior: ScrollBehavior = 'smooth'): boolean {
    const el = document.getElementById(id);
    if (!el) return false;
    el.scrollIntoView({ behavior, block: 'start' });
    return true;
}

export function isLandingSectionId(id: string): id is LandingSectionId {
    return (LANDING_SECTION_IDS as readonly string[]).includes(id);
}
