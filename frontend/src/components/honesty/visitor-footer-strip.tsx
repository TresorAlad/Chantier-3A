import React from 'react';
import { Link } from 'react-router-dom';

/** Bandeau discret en bas de la vitrine publique (sans jargon technique). */
const VisitorFooterStrip = ({ className = '' }: { className?: string }) => (
    <aside
        aria-label="Informations festival"
        className={`border-t border-border bg-muted/40 px-4 py-4 text-center text-sm text-muted-foreground sm:px-6 ${className}`}
    >
        <p>
            Billetterie officielle <strong className="font-semibold text-foreground">Tdev Festival 2026</strong> · Lomé,
            21-22 novembre ·{' '}
            <Link to="/contact" className="font-medium text-primary-emphasis underline-offset-4 hover:underline">
                Contact
            </Link>
        </p>
    </aside>
);

export default VisitorFooterStrip;
