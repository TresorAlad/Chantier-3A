import type { Transition, Variants } from 'framer-motion';

export const EASE_EMPHASIZED = [0.2, 0, 0, 1] as const;
export const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const;

export const transitionFast: Transition = { duration: 0.24, ease: EASE_EMPHASIZED };
export const transitionMedium: Transition = { duration: 0.42, ease: EASE_OUT_EXPO };
export const transitionSlow: Transition = { duration: 0.55, ease: EASE_OUT_EXPO };

export const springSnappy: Transition = { type: 'spring', stiffness: 420, damping: 32, mass: 0.85 };
export const springSoft: Transition = { type: 'spring', stiffness: 260, damping: 28, mass: 0.9 };
/** Carrousel cover flow : rotation et profondeur fluides. */
export const springCoverFlow: Transition = { type: 'spring', stiffness: 340, damping: 34, mass: 0.75 };

export const fadeUp: Variants = {
    hidden: { opacity: 0, y: 28 },
    visible: { opacity: 1, y: 0, transition: transitionMedium },
};

export const fadeIn: Variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: transitionFast },
};

export const scaleIn: Variants = {
    hidden: { opacity: 0, scale: 0.92, y: 12 },
    visible: { opacity: 1, scale: 1, y: 0, transition: springSoft },
};

export const staggerContainer: Variants = {
    hidden: {},
    visible: {
        transition: { staggerChildren: 0.11, delayChildren: 0.06 },
    },
};

export const staggerItem: Variants = {
    hidden: { opacity: 0, y: 24, scale: 0.97 },
    visible: { opacity: 1, y: 0, scale: 1, transition: springSoft },
};

export const pageEnter: Variants = {
    hidden: { opacity: 0, y: 22, filter: 'blur(6px)' },
    enter: { opacity: 1, y: 0, filter: 'blur(0px)', transition: { duration: 0.45, ease: EASE_OUT_EXPO } },
    exit: { opacity: 0, y: -14, filter: 'blur(4px)', transition: { duration: 0.28, ease: EASE_EMPHASIZED } },
};

export const pageEnterReduced: Variants = {
    hidden: { opacity: 1, y: 0, filter: 'blur(0px)' },
    enter: { opacity: 1, y: 0, filter: 'blur(0px)' },
    exit: { opacity: 1, y: 0, filter: 'blur(0px)' },
};

export const stackedCardsContainer: Variants = {
    hidden: {},
    visible: {
        transition: { staggerChildren: 0.07, delayChildren: 0.35 },
    },
};

export const stackedCardItem: Variants = {
    hidden: { opacity: 0, scale: 0.72 },
    visible: {
        opacity: 1,
        scale: 1,
        transition: springSnappy,
    },
};

export const reducedMotionVariants: Variants = {
    hidden: { opacity: 1, y: 0, scale: 1 },
    visible: { opacity: 1, y: 0, scale: 1 },
};

/** Viewport partagé pour les révélations au scroll (vitrine). */
export const scrollRevealViewport = { once: true, margin: '-10% 0px -8% 0px', amount: 0.2 } as const;
