import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { MotionConfig } from 'framer-motion';
import PageTransition from '../motion/page-transition';
import ScrollToHash from '../routing/scroll-to-hash';

/** Facture / billet : pas d'animation de sortie (évite écran blanc après le dialogue pass). */
function isOrderGuestFlow(pathname: string): boolean {
    return /^\/order\/[^/]+\/(facture|billet)\/?$/.test(pathname);
}

// Public / visitor surface. Each page brings its own header/footer (see routes.tsx).
const BlankLayout = () => {
    const { pathname } = useLocation();
    const plainOrderPage = isOrderGuestFlow(pathname);

    return (
        <MotionConfig reducedMotion="user">
            <ScrollToHash />
            <div className="flex min-h-screen flex-col">
                {plainOrderPage ? (
                    <Outlet />
                ) : (
                    <PageTransition>
                        <Outlet />
                    </PageTransition>
                )}
            </div>
        </MotionConfig>
    );
};

export default BlankLayout;
