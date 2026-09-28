import { cn } from '@/lib/utils';

export interface PixelTrameProps {
    className?: string;
}

/** Trame pixel charte (nuage de points, densité variable vers les bords). */
export function PixelTrame({ className }: PixelTrameProps) {
    return <div className={cn('pointer-events-none pixel-trame opacity-60', className)} aria-hidden="true" />;
}
