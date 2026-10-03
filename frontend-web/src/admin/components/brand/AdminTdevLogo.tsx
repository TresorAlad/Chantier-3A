import { cn } from '@/lib/utils';
import {
    TDEV_LOGO_DARK_URL,
    TDEV_LOGO_URL,
    TDEV_TICKET_LOGO_URL,
} from '@/components/brand/tdev-brand-assets';

type AdminLogoVariant = 'onDark' | 'onLight' | 'markOnDark' | 'markOnLight';
type AdminLogoSize = 'sm' | 'md' | 'lg' | 'xl';

const HEIGHT: Record<AdminLogoSize, string> = {
    sm: 'h-7',
    md: 'h-9',
    lg: 'h-11',
    xl: 'h-14 sm:h-16',
};

function logoSrc(variant: AdminLogoVariant): string {
    switch (variant) {
        case 'onDark':
            return TDEV_LOGO_DARK_URL;
        case 'onLight':
            return TDEV_LOGO_URL;
        case 'markOnDark':
            return TDEV_TICKET_LOGO_URL;
        case 'markOnLight':
            return TDEV_TICKET_LOGO_URL;
    }
}

export interface AdminTdevLogoProps {
    variant?: AdminLogoVariant;
    size?: AdminLogoSize;
    className?: string;
    /** Affiche « TDEV Festival » et le sous-titre sous le logo. */
    withTitle?: boolean;
    subtitle?: string;
}

/** Logo officiel TDEV pour l’interface admin (wordmark ou vignette). */
export function AdminTdevLogo({
    variant = 'onLight',
    size = 'md',
    className,
    withTitle = false,
    subtitle,
}: AdminTdevLogoProps) {
    const isMark = variant === 'markOnDark' || variant === 'markOnLight';
    const imgClass = cn(
        'w-auto select-none object-contain object-left',
        isMark ? 'h-9 w-9 rounded-lg object-center' : HEIGHT[size],
        (variant === 'onDark' || variant === 'markOnDark') && 'brightness-0 invert',
        variant === 'markOnLight' && 'dark:invert',
        variant === 'markOnDark' && 'ring-1 ring-white/10 rounded-lg',
    );

    return (
        <div className={cn('flex min-w-0 items-center gap-3', className)}>
            <img src={logoSrc(variant)} alt="TDEV Festival" className={imgClass} decoding="async" />
            {withTitle && (
                <div className="min-w-0">
                    <p
                        className={cn(
                            'truncate font-bold leading-tight',
                            variant === 'onDark' || variant === 'markOnDark'
                                ? 'text-white'
                                : 'text-green-950',
                        )}
                    >
                        TDEV Festival
                    </p>
                    {subtitle && (
                        <p
                            className={cn(
                                'truncate text-[10px] font-semibold uppercase tracking-widest',
                                variant === 'onDark' || variant === 'markOnDark'
                                    ? 'text-green-200'
                                    : 'text-green-700',
                            )}
                        >
                            {subtitle}
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}

export function AdminLoadingScreen({ message = 'Chargement…' }: { message?: string }) {
    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#F8FAFC] px-6">
            <AdminTdevLogo variant="onLight" size="lg" />
            <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-green-800 border-t-transparent" />
                <p className="text-sm text-green-800">{message}</p>
            </div>
        </div>
    );
}
