import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { springSoft } from '@/components/motion/motion-presets';

export type MediaSlotAspect = 'video' | 'square' | 'portrait' | 'wide';
export type MediaSlotTint = 'blue' | 'cyan' | 'violet' | 'orange' | 'pink' | 'neutral';

const ASPECT: Record<MediaSlotAspect, string> = {
    video: 'aspect-video',
    square: 'aspect-square',
    portrait: 'aspect-[3/4]',
    wide: 'aspect-[21/9]',
};

const TINT: Record<MediaSlotTint, string> = {
    blue: 'from-fest-blue/40 via-fest-violet/25 to-black/20',
    cyan: 'from-fest-cyan/45 via-fest-blue/20 to-black/25',
    violet: 'from-fest-violet/45 via-fest-pink/20 to-black/25',
    orange: 'from-fest-orange/40 via-fest-yellow/25 to-black/20',
    pink: 'from-fest-pink/40 via-fest-violet/25 to-black/20',
    neutral: 'from-muted via-muted/80 to-muted/60',
};

export interface MediaSlotProps {
    src?: string | null;
    alt: string;
    aspect?: MediaSlotAspect;
    tint?: MediaSlotTint;
    caption?: string;
    className?: string;
    interactive?: boolean;
    loading?: 'lazy' | 'eager';
}

const MediaSlot = ({
    src,
    alt,
    aspect = 'video',
    tint = 'blue',
    caption,
    className,
    interactive = true,
    loading = 'lazy',
}: MediaSlotProps) => {
    const reduce = useReducedMotion();
    const hasImage = Boolean(src?.trim());

    return (
        <motion.figure
            className={cn(
                'group relative overflow-hidden rounded-2xl border border-border/60 bg-muted shadow-soft',
                ASPECT[aspect],
                className,
            )}
            {...(interactive && !reduce ? { whileHover: { scale: 1.02 }, transition: springSoft } : {})}
        >
            {hasImage ? (
                <img
                    src={src!}
                    alt={alt}
                    className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    loading={loading}
                    decoding="async"
                />
            ) : (
                <div
                    className={cn(
                        'flex h-full w-full flex-col items-center justify-center bg-gradient-to-br p-6 text-center',
                        TINT[tint],
                    )}
                    aria-hidden={caption ? undefined : true}
                >
                    <div className="absolute inset-0 opacity-[0.15] pixel-trame" />
                    <div className="relative flex flex-col items-center gap-2">
                        <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/20 bg-black/20 text-white/90 backdrop-blur-sm">
                            <ImageIcon className="h-5 w-5" aria-hidden="true" />
                        </span>
                        {caption ? (
                            <figcaption className="max-w-[14rem] text-xs font-medium leading-snug text-white/85 sm:text-sm">
                                {caption}
                            </figcaption>
                        ) : null}
                    </div>
                </div>
            )}
            {!hasImage && !caption ? <span className="sr-only">{alt}</span> : null}
        </motion.figure>
    );
};

export default MediaSlot;
