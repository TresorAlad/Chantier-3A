import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Money } from '@/components/ui/money';
import { cn } from '@/lib/utils';
import { springSoft } from '@/components/motion/motion-presets';

type GoodieTone = 'blue' | 'pink' | 'orange';

const PANEL: Record<
    GoodieTone,
    { panel: string; gradient: string }
> = {
    blue: { panel: 'bg-[#0f2d4d]', gradient: 'from-[#0f2d4d] via-[#0f2d4d]/40 to-transparent' },
    pink: { panel: 'bg-[#4a1a3d]', gradient: 'from-[#4a1a3d] via-[#4a1a3d]/40 to-transparent' },
    orange: { panel: 'bg-[#3a2618]', gradient: 'from-[#3a2618] via-[#3a2618]/40 to-transparent' },
};

export interface GoodieCardProps {
    name: string;
    description?: string;
    priceMinor: number;
    currency: string;
    coverSrc: string;
    tags: string[];
    tone?: GoodieTone;
    soldOut?: boolean;
    onAdd: () => void;
}

const GoodieCard = ({
    name,
    description,
    priceMinor,
    currency,
    coverSrc,
    tags,
    tone = 'blue',
    soldOut = false,
    onAdd,
}: GoodieCardProps) => {
    const reduce = useReducedMotion();
    const theme = PANEL[tone];

    return (
        <motion.article
            className={cn(
                'group flex h-full flex-col overflow-hidden rounded-[1.75rem] shadow-elevated ring-1 ring-black/5 dark:ring-white/10',
                soldOut && 'opacity-70',
            )}
            transition={springSoft}
            {...(reduce ? {} : { whileHover: soldOut ? {} : { y: -8 }, whileTap: { scale: 0.99 } })}
        >
            <div className="relative aspect-[4/3] w-full shrink-0 overflow-hidden">
                <img
                    src={coverSrc}
                    alt={name}
                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                    loading="lazy"
                    decoding="async"
                />
                <div className={cn('absolute inset-0 bg-gradient-to-t', theme.gradient)} aria-hidden="true" />
            </div>

            <div className={cn('flex flex-1 flex-col px-5 pb-5 pt-4 text-white', theme.panel)}>
                <div className="flex items-start justify-between gap-3">
                    <h3 className="font-display text-xl font-bold leading-tight">{name}</h3>
                    <span className="shrink-0 rounded-full bg-black/25 px-3 py-1 text-sm font-bold tabular-nums backdrop-blur-sm">
                        <Money minor={priceMinor} currency={currency} />
                    </span>
                </div>
                {description ? <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-white/85">{description}</p> : null}

                <ul className="mt-4 flex flex-wrap gap-2">
                    {tags.map((tag, index) => (
                        <li
                            key={tag}
                            className="inline-flex items-center gap-1 rounded-full border border-white/35 bg-white/10 px-2.5 py-1 text-xs font-medium"
                        >
                            {index === 0 ? <Star className="h-3 w-3 fill-white/90 text-white/90" aria-hidden="true" /> : null}
                            {tag}
                        </li>
                    ))}
                </ul>

                <Button
                    type="button"
                    size="lg"
                    disabled={soldOut}
                    onClick={onAdd}
                    className="mt-5 w-full rounded-full border-0 bg-white text-sm font-bold text-black hover:bg-white/95 disabled:bg-white/50"
                >
                    {soldOut ? 'Épuisé' : 'Ajouter au panier'}
                </Button>
            </div>
        </motion.article>
    );
};

export default GoodieCard;
