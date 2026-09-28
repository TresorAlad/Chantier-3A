import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { pageEnter, pageEnterReduced } from '@/components/motion/motion-presets';

/**
 * Cross-fade + montée légère entre routes vitrine (BlankLayout).
 */
const PageTransition = ({ children, className }: { children: ReactNode; className?: string }) => {
    const location = useLocation();
    const prefersReducedMotion = useReducedMotion();
    const variants = prefersReducedMotion ? pageEnterReduced : pageEnter;

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key={`${location.pathname}${location.search}`}
                className={className}
                variants={variants}
                initial={false}
                animate="enter"
                exit="exit"
            >
                {children}
            </motion.div>
        </AnimatePresence>
    );
};

export default PageTransition;
