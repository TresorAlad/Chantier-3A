import React from 'react';
import { Link, type LinkProps, useLocation } from 'react-router-dom';
import { landingSectionTo, scrollToLandingSection, type LandingSectionId } from '@/lib/landing-nav';

type LandingSectionLinkProps = Omit<LinkProps, 'to'> & {
    section: LandingSectionId;
};

/** Lien vers une section de la landing ; re-scroll si le hash est déjà actif. */
const LandingSectionLink = ({ section, onClick, ...props }: LandingSectionLinkProps) => {
    const location = useLocation();
    const to = landingSectionTo(section);
    const hash = to.hash;

    return (
        <Link
            {...props}
            to={to}
            onClick={(e) => {
                onClick?.(e);
                if (location.pathname === '/' && location.hash === hash) {
                    e.preventDefault();
                    scrollToLandingSection(section);
                }
            }}
        />
    );
};

export default LandingSectionLink;
