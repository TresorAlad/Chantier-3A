import React from 'react';
import { Facebook, Instagram, Linkedin, Twitter, Youtube, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { getPublicSocialLinks, type PublicSocialLink, type SocialNetworkId } from '@/lib/public-links';

const ICONS: Record<SocialNetworkId, LucideIcon> = {
    linkedin: Linkedin,
    youtube: Youtube,
    twitter: Twitter,
    facebook: Facebook,
    instagram: Instagram,
};

export type TdevSocialLinksProps = {
    className?: string;
    iconClassName?: string;
    /** Boutons ronds bordés (footer) ou discrets (section édition). */
    variant?: 'footer' | 'onDark';
};

function SocialIconButton({
    link,
    variant,
    iconClassName,
}: {
    link: PublicSocialLink;
    variant: NonNullable<TdevSocialLinksProps['variant']>;
    iconClassName?: string | undefined;
}) {
    const Icon = ICONS[link.id];
    const isFooter = variant === 'footer';

    return (
        <a
            href={link.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={link.label}
            className={cn(
                'inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors',
                isFooter
                    ? 'border border-border bg-card text-foreground hover:border-primary hover:bg-accent hover:text-primary-emphasis dark:border-white/20 dark:bg-white/5 dark:hover:border-fest-cyan/50 dark:hover:bg-white/10 dark:hover:text-fest-cyan'
                    : 'border border-white/25 bg-white/10 text-white hover:border-white/50 hover:bg-white/20',
                iconClassName,
            )}
        >
            <Icon className="h-5 w-5" aria-hidden="true" />
        </a>
    );
}

export function TdevSocialLinks({ className, iconClassName, variant = 'footer' }: TdevSocialLinksProps) {
    const links = getPublicSocialLinks();
    return (
        <div className={cn('flex flex-wrap gap-2', className)}>
            {links.map((link) => (
                <SocialIconButton key={link.id} link={link} variant={variant} iconClassName={iconClassName} />
            ))}
        </div>
    );
}
