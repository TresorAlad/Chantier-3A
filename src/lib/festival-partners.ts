/** Partenaires affichés sur la vitrine (alignés sur ourtdev.com). */

export type PartnerLogoTreatment = 'surface' | 'mono' | 'color';

export type FestivalPartner = {
    id: string;
    name: string;
    href?: string;
    logoSrc: string;
    /** Rendu logo sur fond clair / fond sombre sans cadre blanc. */
    treatment: PartnerLogoTreatment;
};

const base = '/partners';

export const FESTIVAL_PARTNERS: FestivalPartner[] = [
    {
        id: 'flutterease',
        name: 'Flutterease',
        logoSrc: `${base}/flutterease.png`,
        treatment: 'surface',
    },
    {
        id: 'propel',
        name: 'PROPEL',
        logoSrc: `${base}/propel.png`,
        treatment: 'mono',
    },
    {
        id: 'pandore',
        name: 'PANDORE',
        logoSrc: `${base}/pandore.png`,
        treatment: 'mono',
    },
    {
        id: 'klic',
        name: 'KLIC',
        logoSrc: `${base}/klic.png`,
        treatment: 'mono',
    },
    {
        id: 'datacamp-donates',
        name: 'DataCamp Donates',
        href: 'https://www.datacamp.com/donates',
        logoSrc: `${base}/datacamp-donates.svg`,
        treatment: 'mono',
    },
    {
        id: 'chaoss',
        name: 'CHAOSS',
        href: 'https://chaoss.community/',
        logoSrc: `${base}/chaoss.png`,
        treatment: 'color',
    },
    {
        id: 'jetbrains',
        name: 'JetBrains',
        href: 'https://www.jetbrains.com/',
        logoSrc: `${base}/jetbrains.svg`,
        treatment: 'color',
    },
];
