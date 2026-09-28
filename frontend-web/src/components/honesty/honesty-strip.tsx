import React from 'react';
import { AlertTriangle } from 'lucide-react';
import {
    BUILD_STATUS_LABEL,
    BUILD_STATUS_DETAIL,
    CROSS_GATE_LIMIT_LABEL,
    CROSS_GATE_LIMIT_DETAIL,
} from './claims';
import { cn } from '@/lib/utils';

export interface HonestyStripProps {
    className?: string;
}

/**
 * Bandeau d'information produit (non masquable) - déploiement et limites porte.
 * Placé en fin de flux vitrine pour ne pas chevaucher le header fixe.
 */
const HonestyStrip = ({ className }: HonestyStripProps) => {
    return (
        <aside
            aria-label="Statut de déploiement et limites connues"
            className={cn(
                'border-y border-border/90 bg-muted/70 px-4 py-3.5 text-sm text-muted-foreground sm:px-6',
                'print:hidden',
                className,
            )}
        >
            <div className="mx-auto flex max-w-6xl items-start gap-3 sm:gap-4">
                <AlertTriangle
                    className="mt-0.5 h-4 w-4 shrink-0 text-primary-emphasis sm:mt-1"
                    aria-hidden="true"
                />
                <div className="grid min-w-0 flex-1 gap-3 sm:grid-cols-2 sm:gap-0">
                    <p className="leading-relaxed sm:pr-8">
                        <span className="font-semibold text-foreground">{BUILD_STATUS_LABEL}</span>{' '}
                        {BUILD_STATUS_DETAIL}
                    </p>
                    <p className="leading-relaxed sm:border-l sm:border-border/80 sm:pl-8">
                        <span className="font-semibold text-foreground">{CROSS_GATE_LIMIT_LABEL}</span>{' '}
                        {CROSS_GATE_LIMIT_DETAIL}
                    </p>
                </div>
            </div>
        </aside>
    );
};

export default HonestyStrip;
