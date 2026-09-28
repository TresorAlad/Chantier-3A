import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Money } from '@/components/ui/money';
import { cn } from '@/lib/utils';
import { springSoft } from '@/components/motion/motion-presets';
import type { PassTierId } from '@/lib/festival-storefront';

const TIER_PANEL: Record<
    PassTierId,
    { panel: string; gradient: string; pricePill?: boolean }
> = {
    student: {
        panel: 'bg-[#0c4a52]',
        gradient: 'from-[#0c4a52] via-[#0c4a52]/25 to-transparent',
    },
    standard: {
        panel: 'bg-[#0f2d4d]',
        gradient: 'from-[#0f2d4d] via-[#0f2d4d]/25 to-transparent',
    },
    vip: {
        panel: 'bg-[#3a2618]',
        gradient: 'from-[#3a2618] via-[#3a2618]/25 to-transparent',
        pricePill: true,
    },
};

export interface PassCardProps {
    tier: PassTierId;
    label: string;
    imageAlt?: string;
    description: string;
    priceMinor: number;
    currency: string;
    tags: string[];
    ctaLabel: string;
    onCta: () => void;
    ctaDisabled?: boolean;
    coverSrc: string;
}

const PassCard = ({
    tier,
    label,
    description,
    priceMinor,
    currency,
    tags,
    ctaLabel,
    onCta,
    ctaDisabled = false,
    coverSrc,
    imageAlt,
}: PassCardProps) => {
    const reduce = useReducedMotion();
    const theme = TIER_PANEL[tier];
    const isFree = priceMinor === 0;

    return (
        <motion.article
            className="group flex h-full flex-col overflow-hidden rounded-[1.75rem] shadow-elevated ring-1 ring-black/5 transition-shadow duration-300 hover:shadow-floating dark:ring-white/10"
            transition={springSoft}
            {...(reduce ? {} : { whileHover: { y: -8 }, whileTap: { scale: 0.99 } })}
        >
            <div className="relative aspect-[5/4] w-full shrink-0 overflow-hidden sm:aspect-[4/3]">
                <img
                    src={coverSrc}
                    alt={imageAlt ?? `Illustration ${label}`}
                    className="h-full w-full object-cover object-center transition-transform duration-700 group-hover:scale-[1.03]"
                    loading="lazy"
                    decoding="async"
                />
                <div className={cn('absolute inset-0 bg-gradient-to-t', theme.gradient)} aria-hidden="true" />
            </div>

            <div className={cn('flex flex-1 flex-col px-5 pb-5 pt-4 text-white', theme.panel)}>
                <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-xl font-bold leading-tight tracking-tight">{label}</h3>
                    {theme.pricePill ? (
                        <span className="shrink-0 rounded-full bg-black/25 px-3 py-1 text-sm font-bold tabular-nums backdrop-blur-sm">
                            {isFree ? 'Gratuit' : <Money minor={priceMinor} currency={currency} />}
                        </span>
                    ) : (
                        <span className="shrink-0 font-display text-lg font-bold tabular-nums">
                            {isFree ? 'Gratuit' : <Money minor={priceMinor} currency={currency} />}
                        </span>
                    )}
                </div>

                <p className="mt-2 text-sm leading-relaxed text-white/85">{description}</p>

                <ul className="mt-4 flex flex-wrap gap-2">
                    {tags.map((tag, index) => (
                        <li
                            key={tag}
                            className="inline-flex items-center gap-1 rounded-full border border-white/35 bg-white/10 px-2.5 py-1 text-xs font-medium text-white/95"
                        >
                            {index === 0 ? (
                                <Star className="h-3 w-3 fill-white/90 text-white/90" aria-hidden="true" />
                            ) : null}
                            {tag}
                        </li>
                    ))}
                </ul>

                <Button
                    type="button"
                    size="lg"
                    onClick={onCta}
                    disabled={ctaDisabled}
                    className="mt-5 w-full rounded-full border-0 bg-white text-sm font-bold text-black shadow-none hover:bg-white/95 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
                >
                    {ctaLabel}
                </Button>
            </div>
        </motion.article>
    );
};

export default PassCard;
