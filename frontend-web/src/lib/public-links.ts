/** Chemins et URLs publiques (vitrine), configurables via Vite env. */

import { getOptionalEnv, getOptionalHttpsUrl } from '@/lib/env';

const DEFAULT_STAFF_AUTH_PATH = '/acces-equipe';

/** Réseaux T-Dev (surcharge possible via VITE_* dans .env). */
export const TDEV_SOCIAL_DEFAULTS = {
    linkedin: 'https://www.linkedin.com/company/tdevorg',
    youtube: 'https://www.youtube.com/@tdevcommunity',
    twitter: 'https://twitter.com/tdev228',
    facebook: 'https://www.facebook.com/Tdev228',
} as const;

export type SocialNetworkId = 'linkedin' | 'youtube' | 'twitter' | 'facebook' | 'instagram';

export type PublicSocialLink = {
    id: SocialNetworkId;
    href: string;
    label: string;
};

function normalizePath(path: string): string {
    const trimmed = path.trim();
    if (!trimmed.startsWith('/')) return DEFAULT_STAFF_AUTH_PATH;
    const withoutTrailing = trimmed.replace(/\/+$/, '');
    return withoutTrailing || DEFAULT_STAFF_AUTH_PATH;
}

/** URL de connexion staff (non linkée depuis la vitrine). */
export function getStaffSignInPath(): string {
    const raw = getOptionalEnv('VITE_STAFF_AUTH_PATH');
    if (raw) return normalizePath(raw);
    return DEFAULT_STAFF_AUTH_PATH;
}

function socialUrl(envKey: keyof ImportMetaEnv, fallback: string): string {
    return getOptionalHttpsUrl(envKey) ?? fallback;
}

export function getLinkedInUrl(): string {
    return socialUrl('VITE_LINKEDIN_URL', TDEV_SOCIAL_DEFAULTS.linkedin);
}

export function getYoutubeUrl(): string {
    return socialUrl('VITE_YOUTUBE_URL', TDEV_SOCIAL_DEFAULTS.youtube);
}

export function getTwitterUrl(): string {
    return socialUrl('VITE_TWITTER_URL', TDEV_SOCIAL_DEFAULTS.twitter);
}

export function getFacebookUrl(): string {
    return socialUrl('VITE_FACEBOOK_URL', TDEV_SOCIAL_DEFAULTS.facebook);
}

export function getInstagramUrl(): string | null {
    return getOptionalHttpsUrl('VITE_INSTAGRAM_URL') ?? null;
}

/** Liens affichés dans le footer, contact et sections « Réseaux ». */
export function getPublicSocialLinks(): PublicSocialLink[] {
    const links: PublicSocialLink[] = [
        { id: 'linkedin', href: getLinkedInUrl(), label: 'T-Dev sur LinkedIn' },
        { id: 'youtube', href: getYoutubeUrl(), label: 'T-Dev sur YouTube' },
        { id: 'twitter', href: getTwitterUrl(), label: 'T-Dev sur X (Twitter)' },
        { id: 'facebook', href: getFacebookUrl(), label: 'T-Dev sur Facebook' },
    ];
    const instagram = getInstagramUrl();
    if (instagram) {
        links.push({ id: 'instagram', href: instagram, label: 'T-Dev sur Instagram' });
    }
    return links;
}

export const FESTIVAL_SITE_LABEL = 'festival.ourtdev.com';
export const FESTIVAL_HASHTAG = '#TDEVFESTIVAL2026';
