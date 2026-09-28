import React from 'react';
import { TDEV_TICKET_LOGO_URL } from '@/components/brand/tdev-brand-assets';

export function FestivalPassTicketFooter() {
    return (
        <div className="flex items-end justify-between px-1 pb-1 pt-10">
            <img
                src={TDEV_TICKET_LOGO_URL}
                alt="Tdev"
                className="h-7 w-auto opacity-90"
                crossOrigin="anonymous"
                width={120}
                height={28}
            />
            <span className="text-sm font-medium text-muted-foreground">#TDev2026</span>
        </div>
    );
}
