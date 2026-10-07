import type { ReactNode } from 'react';
import { AdminTdevLogo } from './AdminTdevLogo';
import { adminTheme } from '../../lib/admin-theme';
import { cn } from '../../lib/utils';

/** Carte centrée avec logo pour login, invitation, OAuth. */
export function AdminAuthShell(props: { children: ReactNode; title: string; description?: string }) {
    return (
        <div className={cn('admin-app flex min-h-screen items-center justify-center p-6', adminTheme.canvas)}>
            <div className="w-full max-w-md">
                <div className="mb-6 flex justify-center">
                    <AdminTdevLogo variant="onLight" size="lg" />
                </div>
                <div className={cn(adminTheme.card, 'p-8 shadow-[0_8px_30px_rgba(15,23,42,0.06)]')}>
                    <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">{props.title}</h1>
                    {props.description && (
                        <p className="mt-2 text-sm text-zinc-500">{props.description}</p>
                    )}
                    <div className="mt-6">{props.children}</div>
                </div>
            </div>
        </div>
    );
}
