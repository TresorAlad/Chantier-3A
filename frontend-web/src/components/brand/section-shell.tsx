import React from 'react';
import { cn } from '@/lib/utils';
import LandingSectionHeader from '@/components/brand/landing-section-header';

export interface SectionShellProps {
    id?: string;
    eyebrow?: string;
    title: string;
    description?: string;
    className?: string;
    children?: React.ReactNode;
    tone?: 'light' | 'muted';
    align?: 'center' | 'left';
}

const SectionShell = ({
    id,
    eyebrow,
    title,
    description,
    className,
    children,
    tone = 'light',
    align = 'center',
}: SectionShellProps) => {
    return (
        <section
            id={id}
            className={cn(
                'scroll-mt-24 py-16 sm:py-24',
                tone === 'muted' ? 'bg-muted/50' : 'bg-background',
                className,
            )}
        >
            <div className="container mx-auto px-4">
                <LandingSectionHeader
                    title={title}
                    align={align}
                    {...(eyebrow ? { eyebrow } : {})}
                    {...(description ? { description } : {})}
                />
                {children}
            </div>
        </section>
    );
};

export default SectionShell;
