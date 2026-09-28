import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { isLandingSectionId, scrollToLandingSection } from '@/lib/landing-nav';

/** Après navigation SPA, scroll vers l'élément `id` du hash (ex. /#passes). */
const ScrollToHash = () => {
    const { pathname, hash } = useLocation();

    useEffect(() => {
        if (!hash) return;
        const id = decodeURIComponent(hash.replace(/^#/, ''));
        if (!isLandingSectionId(id)) return;

        const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        const behavior: ScrollBehavior = prefersReduced ? 'auto' : 'smooth';
        const delay = pathname === '/' ? 80 : 520;

        const timer = window.setTimeout(() => {
            scrollToLandingSection(id, behavior);
        }, delay);

        return () => window.clearTimeout(timer);
    }, [pathname, hash]);

    return null;
};

export default ScrollToHash;
