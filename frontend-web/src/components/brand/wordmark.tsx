import type { HTMLAttributes, ImgHTMLAttributes } from 'react';
import { cn } from '@/lib/utils';
import { useResolvedTheme } from '@/components/brand/use-resolved-theme';

const LOGO_DARK = '/brand/tdev-festival-2026-dark.svg';
const LOGO_LIGHT = '/brand/tdev-festival-2026-light.svg';

type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl';
type Tone = 'auto' | 'onDark' | 'onLight';

const SIZES: Record<Size, { logo: string; gap: string; minH: string }> = {
    xs: { logo: 'h-6 min-h-[24px]', gap: 'gap-1.5', minH: 'min-h-[24px]' },
    sm: { logo: 'h-7 min-h-[24px]', gap: 'gap-2', minH: 'min-h-[24px]' },
    md: { logo: 'h-8 min-h-[24px]', gap: 'gap-2', minH: 'min-h-[24px]' },
    lg: { logo: 'h-10 min-h-[24px]', gap: 'gap-2.5', minH: 'min-h-[24px]' },
    xl: { logo: 'h-12 min-h-[24px] sm:h-14', gap: 'gap-3', minH: 'min-h-[24px]' },
};

const stepFor = (size: Size) => SIZES[size] ?? SIZES['md'];

function logoForTone(tone: Tone, resolvedTheme: 'light' | 'dark') {
    if (tone === 'onLight') return LOGO_LIGHT;
    if (tone === 'onDark') return LOGO_DARK;
    return resolvedTheme === 'dark' ? LOGO_DARK : LOGO_LIGHT;
}

interface WordmarkProps extends HTMLAttributes<HTMLSpanElement> {
    size?: Size;
    tone?: Tone;
    hideWordBelowSm?: boolean;
}

export function Wordmark({ size = 'md', tone = 'auto', hideWordBelowSm = false, className, ...props }: WordmarkProps) {
    const step = stepFor(size);
    const resolvedTheme = useResolvedTheme();
    return (
        <span className={cn('inline-flex items-center', step.minH, className)} {...props}>
            <img
                src={logoForTone(tone, resolvedTheme)}
                alt="Tdev Festival 2026"
                className={cn('w-auto shrink-0 select-none object-left object-contain', step.logo, hideWordBelowSm ? 'sr-only sm:not-sr-only sm:inline' : '')}
            />
            {hideWordBelowSm ? <span className="sr-only sm:hidden">Tdev Festival 2026</span> : null}
        </span>
    );
}

interface LogoTileProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src' | 'width' | 'height' | 'size'> {
    size?: Size;
    tone?: Tone;
}

export function LogoTile({ size = 'md', tone = 'onDark', alt = '', className, ...props }: LogoTileProps) {
    const step = stepFor(size);
    const resolvedTheme = useResolvedTheme();
    return (
        <img
            src={logoForTone(tone, resolvedTheme)}
            alt={alt}
            width={420}
            height={48}
            className={cn('shrink-0 select-none object-left object-contain', step.logo, 'w-auto', className)}
            {...props}
        />
    );
}

interface BrandLockupProps extends HTMLAttributes<HTMLSpanElement> {
    size?: Size;
    tone?: Tone;
    hideWordBelowSm?: boolean;
}

export function BrandLockup({ size = 'md', tone = 'auto', hideWordBelowSm = false, className, ...props }: BrandLockupProps) {
    return <Wordmark size={size} tone={tone} hideWordBelowSm={hideWordBelowSm} className={className} {...props} />;
}

interface BrandTaglineProps extends HTMLAttributes<HTMLParagraphElement> {
    tone?: 'onDark' | 'onLight';
}

export function BrandTagline({ tone = 'onDark', className, ...props }: BrandTaglineProps) {
    return (
        <p
            className={cn(
                'font-accent text-sm leading-snug sm:text-base',
                tone === 'onDark' ? 'text-brand-ink/80' : 'text-muted-foreground',
                className,
            )}
            {...props}
        >
            <span className="block">Façonné avec cœur.</span>
            <span className="block">Par la communauté.</span>
        </p>
    );
}

export default BrandLockup;
