import React from 'react';
import { cn } from '@/lib/utils';
import { PartnerLogo } from '@/components/brand/partner-logo';
import { FESTIVAL_PARTNERS } from '@/lib/festival-partners';

function PartnerTrack({ trackKey, duplicate }: { trackKey: string; duplicate?: boolean }) {
    return (
        <ul className="flex shrink-0 list-none items-center" aria-hidden={duplicate ? true : undefined}>
            {FESTIVAL_PARTNERS.map((partner) => (
                <li key={`${trackKey}-${partner.id}`} className="flex shrink-0 items-center">
                    <PartnerLogo partner={partner} variant="marquee" />
                </li>
            ))}
        </ul>
    );
}

/** Logos partenaires en ligne, défilement continu (style ourtdev.com). */
export function PartnersMarquee({ className }: { className?: string }) {
    return (
        <div
            className={cn('relative w-full overflow-hidden py-2', className)}
            role="region"
            aria-label="Logos des partenaires T-Dev"
        >
            <div
                className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-gradient-to-r from-background via-background/80 to-transparent motion-reduce:hidden sm:w-16"
                aria-hidden="true"
            />
            <div
                className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-gradient-to-l from-background via-background/80 to-transparent motion-reduce:hidden sm:w-16"
                aria-hidden="true"
            />

            <div className="hidden motion-reduce:flex motion-reduce:flex-wrap motion-reduce:items-center motion-reduce:justify-center motion-reduce:gap-x-4 motion-reduce:gap-y-2">
                <PartnerTrack trackKey="static" />
            </div>

            <div className="flex w-max items-center motion-reduce:hidden motion-safe:animate-partner-marquee">
                <PartnerTrack trackKey="a" />
                <PartnerTrack trackKey="b" duplicate />
            </div>

            <ul className="sr-only">
                {FESTIVAL_PARTNERS.map((partner) => (
                    <li key={partner.id}>{partner.name}</li>
                ))}
            </ul>
        </div>
    );
}
