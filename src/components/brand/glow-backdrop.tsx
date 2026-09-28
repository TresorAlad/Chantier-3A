import React from 'react';
import { cn } from '@/lib/utils';
import { PixelTrame } from '@/components/brand/pixel-trame';

export interface GlowBackdropProps {
    className?: string;
    showTrame?: boolean;
    intensity?: 'soft' | 'strong';
}

const GlowBackdrop = ({ className, showTrame = true, intensity = 'soft' }: GlowBackdropProps) => (
    <div className={cn('pointer-events-none absolute inset-0 overflow-hidden', className)} aria-hidden="true">
        <div
            className={cn(
                'hero-blob-breathe absolute -top-1/4 left-1/2 h-[70rem] w-[70rem] rounded-full blur-[120px]',
                intensity === 'strong' ? 'bg-fest-blue/30' : 'bg-fest-blue/20',
            )}
        />
        {showTrame ? <PixelTrame className="absolute bottom-0 left-0 h-2/5 w-2/5 opacity-40 motion-safe:animate-pulse" /> : null}
        <div className="hero-glow hero-glow-drift absolute inset-0" />
    </div>
);

export default GlowBackdrop;
