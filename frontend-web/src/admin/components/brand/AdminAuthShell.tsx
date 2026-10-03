import type { ReactNode } from 'react';
import { AdminTdevLogo } from './AdminTdevLogo';

/** Carte centrée avec logo pour login, invitation, OAuth. */
export function AdminAuthShell(props: { children: ReactNode; title: string; description?: string }) {
    return (
        <div className="flex min-h-screen items-center justify-center bg-[#f7fcf8] p-6">
            <div className="w-full max-w-md">
                <div className="mb-6 flex justify-center">
                    <AdminTdevLogo variant="onLight" size="lg" />
                </div>
                <div className="rounded-3xl border border-green-100 bg-white p-8 shadow-lg shadow-green-950/5">
                    <h1 className="text-2xl font-black text-green-950">{props.title}</h1>
                    {props.description && (
                        <p className="mt-2 text-sm text-green-800">{props.description}</p>
                    )}
                    <div className="mt-6">{props.children}</div>
                </div>
            </div>
        </div>
    );
}
