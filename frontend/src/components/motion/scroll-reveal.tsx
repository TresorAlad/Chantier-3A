import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { fadeUp, scaleIn, scrollRevealViewport, transitionMedium } from '@/components/motion/motion-presets';

type RevealVariant = 'fadeUp' | 'scaleIn';

export interface ScrollRevealProps {
    children: ReactNode;
    className?: string;
    delay?: number;
    variant?: RevealVariant;
    as?: 'div' | 'section' | 'li';
    /** Entrée au montage (pages panier/checkout), sans attendre le scroll. */
    immediate?: boolean;
}

const VARIANTS = { fadeUp, scaleIn } as const;

export function ScrollReveal({
    children,
    className,
    delay = 0,
    variant = 'fadeUp',
    as = 'div',
    immediate = false,
}: ScrollRevealProps) {
    const reduce = useReducedMotion();
    const MotionTag = motion[as];
    const presets = VARIANTS[variant];

    const motionProps = reduce
        ? {}
        : immediate
          ? { animate: 'visible' as const, variants: presets }
          : { whileInView: 'visible' as const, variants: presets, viewport: scrollRevealViewport };

    return (
        <MotionTag className={cn(className)} initial={reduce ? false : 'hidden'} transition={{ ...transitionMedium, delay }} {...motionProps}>
            {children}
        </MotionTag>
    );
}

export default ScrollReveal;
