import type { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { TDEV_LOGO_DARK_URL, TDEV_LOGO_URL } from '@/components/brand/tdev-brand-assets';
import { useResolvedTheme } from '@/components/brand/use-resolved-theme';

type TdevLogoSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

const HEIGHT: Record<TdevLogoSize, string> = {
    xs: 'h-6',
    sm: 'h-7',
    md: 'h-8',
    lg: 'h-10',
    xl: 'h-12 sm:h-14',
};

export interface TdevLogoProps extends HTMLAttributes<HTMLSpanElement> {
    size?: TdevLogoSize;
}

/** Logo Tdev transparent, variante claire / sombre selon le thème. */
export function TdevLogo({ size = 'md', className, ...props }: TdevLogoProps) {
    const resolvedTheme = useResolvedTheme();
    const src = resolvedTheme === 'dark' ? TDEV_LOGO_DARK_URL : TDEV_LOGO_URL;

    return (
        <span className={cn('inline-flex shrink-0 items-center', className)} {...props}>
            <img
                src={src}
                alt="Tdev"
                width={120}
                height={40}
                className={cn('w-auto select-none object-contain object-left', HEIGHT[size])}
                decoding="async"
            />
        </span>
    );
}
