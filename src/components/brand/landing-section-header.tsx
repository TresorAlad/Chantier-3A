import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { fadeUp, transitionMedium } from '@/components/motion/motion-presets';

export interface LandingSectionHeaderProps {
    eyebrow?: string;
    title: string;
    description?: string;
    align?: 'center' | 'left';
    className?: string;
}

const LandingSectionHeader = ({
    eyebrow,
    title,
    description,
    align = 'center',
    className,
}: LandingSectionHeaderProps) => {
    const reduce = useReducedMotion();
    return (
        <motion.header
            className={cn(
                'mb-10 sm:mb-12',
                align === 'center' && 'mx-auto max-w-2xl text-center',
                align === 'left' && 'max-w-3xl text-left',
                className,
            )}
            initial={reduce ? false : 'hidden'}
            viewport={{ once: true, margin: '-8%' }}
            transition={transitionMedium}
            {...(reduce ? {} : { whileInView: 'visible', variants: fadeUp })}
        >
            {eyebrow ? (
                <span className="inline-flex rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-primary-emphasis">
                    {eyebrow}
                </span>
            ) : null}
            <h2 className="mt-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
            {description ? (
                <p className="mt-3 text-base leading-relaxed text-muted-foreground sm:text-lg">{description}</p>
            ) : null}
        </motion.header>
    );
};

export default LandingSectionHeader;
