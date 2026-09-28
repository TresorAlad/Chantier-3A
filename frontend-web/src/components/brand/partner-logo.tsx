import React from 'react';
import { cn } from '@/lib/utils';
import type { FestivalPartner, PartnerLogoTreatment } from '@/lib/festival-partners';

const treatmentClass: Record<PartnerLogoTreatment, string> = {
    /** Logos exportés avec fond blanc : fond « transparent » visuellement. */
    surface: cn(
        'mix-blend-multiply contrast-[1.02] saturate-[1.05]',
        'dark:mix-blend-screen dark:brightness-110 dark:saturate-110 dark:contrast-100',
    ),
    /** Logos sombres ou SVG currentColor : lisibles en clair et en sombre. */
    mono: 'opacity-90 dark:brightness-0 dark:invert',
    /** Logos multicolores (CHAOSS, JetBrains). */
    color: 'opacity-95 saturate-[0.92] dark:brightness-[1.12] dark:saturate-[1.05]',
};

export type PartnerLogoProps = {
    partner: FestivalPartner;
    className?: string;
    /** Bandeau horizontal : pas de carte, hauteur uniforme. */
    variant?: 'tile' | 'marquee';
};

export function PartnerLogo({ partner, className, variant = 'tile' }: PartnerLogoProps) {
    const img = (
        <img
            src={partner.logoSrc}
            alt={partner.name}
            loading="lazy"
            decoding="async"
            draggable={false}
            className={cn(
                variant === 'marquee'
                    ? 'h-9 w-auto max-h-9 max-w-[min(200px,36vw)] object-contain object-center sm:h-10 sm:max-h-10 sm:max-w-[220px]'
                    : 'h-10 w-auto max-w-[148px] object-contain object-center sm:h-11 sm:max-w-[168px]',
                treatmentClass[partner.treatment],
            )}
        />
    );

    const tileClass = cn(
        'flex min-h-[88px] items-center justify-center rounded-2xl border border-border/80 bg-card/40 px-6 py-5',
        'transition-colors hover:border-primary/35 hover:bg-card/70',
        'dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-fest-cyan/30 dark:hover:bg-white/[0.06]',
        className,
    );

    const marqueeClass = cn(
        'flex h-14 shrink-0 items-center justify-center px-8 sm:h-16 sm:px-12',
        'transition-opacity hover:opacity-80',
        className,
    );

    const wrapperClass = variant === 'marquee' ? marqueeClass : tileClass;

    if (partner.href) {
        return (
            <a
                href={partner.href}
                target="_blank"
                rel="noopener noreferrer"
                className={wrapperClass}
                aria-label={`${partner.name} (nouvelle fenêtre)`}
            >
                {img}
            </a>
        );
    }

    return (
        <div className={wrapperClass} aria-label={partner.name}>
            {img}
        </div>
    );
}
