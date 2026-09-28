import React from 'react';
import { format } from 'date-fns';
import { fr } from 'date-fns/locale';
import { ScanLine } from 'lucide-react';
import { TDEV_TICKET_LOGO_URL } from '@/components/brand/tdev-brand-assets';

export { TDEV_TICKET_LOGO_URL };

function displayPassLabel(raw: string): string {
    const n = raw.trim().toLowerCase();
    if (!n) return 'Pass standard';
    if (n.includes('vip')) return 'Pass VIP';
    if (n.includes('étudiant') || n.includes('etudiant') || n.includes('student')) return 'Pass étudiant';
    if (n.includes('standard')) return 'Pass standard';
    return raw.trim();
}

function formatEventWhen(iso: string | null | undefined): string | null {
    if (!iso) return null;
    try {
        const d = new Date(iso);
        const day = format(d, 'EEEE, d MMM', { locale: fr });
        const time = format(d, 'h:mm a', { locale: fr });
        return `${day} | ${time}`;
    } catch {
        return null;
    }
}

function TicketPerforation({ notchBg }: { notchBg: string }) {
    return (
        <div className="relative bg-neutral-100 py-1" aria-hidden="true">
            <div className="border-t border-dashed border-neutral-300" />
            <span className={`pointer-events-none absolute -left-3 top-1/2 h-6 w-6 -translate-y-1/2 rounded-full ${notchBg}`} />
            <span className={`pointer-events-none absolute -right-3 top-1/2 h-6 w-6 -translate-y-1/2 rounded-full ${notchBg}`} />
        </div>
    );
}

export interface FestivalPassTicketCardProps {
    eventTitle: string;
    firstName: string;
    lastName: string;
    passLabel: string;
    serial: string;
    status?: string;
    startsAt?: string | null;
    venue?: string;
    address?: string;
    /** Couleur des encoches (doit matcher le fond de la page). */
    notchBgClassName?: string;
    className?: string;
}

export function FestivalPassTicketCard({
    eventTitle,
    firstName,
    lastName,
    passLabel,
    serial,
    status,
    startsAt,
    venue,
    address,
    notchBgClassName = 'bg-neutral-950',
    className = '',
}: FestivalPassTicketCardProps) {
    const isVoid = Boolean(status && status !== 'valid');
    const fullName = `${firstName} ${lastName}`.trim() || 'Participant';
    const pass = displayPassLabel(passLabel);
    const when = formatEventWhen(startsAt);
    const venueLine = [venue?.trim(), address?.trim()].filter(Boolean).join(', ') || 'Lieu à confirmer';

    return (
        <article
            className={`print-keep-color mx-auto w-full max-w-sm overflow-hidden rounded-3xl border border-neutral-200 bg-white text-neutral-900 shadow-[0_24px_64px_rgba(0,0,0,0.45)] ${className}`}
            aria-label={`Billet ${serial} pour ${fullName}`}
        >
            <div
                className="border-b border-emerald-700/30 bg-gradient-to-br from-emerald-500 via-emerald-600 to-emerald-800 px-6 py-6"
                aria-hidden="true"
            />

            <div className="flex gap-3.5 bg-white px-5 pb-2 pt-5">
                <div className="h-[4.25rem] w-[4.25rem] shrink-0 overflow-hidden rounded-lg ring-1 ring-neutral-200">
                    <img
                        src={TDEV_TICKET_LOGO_URL}
                        alt="Tdev"
                        className="h-full w-full object-cover"
                        width={68}
                        height={68}
                        crossOrigin="anonymous"
                    />
                </div>
                <div className="min-w-0 flex-1 pt-0.5">
                    <h2 className="line-clamp-2 font-sans text-[1.05rem] font-bold leading-snug tracking-tight text-neutral-900">
                        {eventTitle}
                    </h2>
                    <p className="mt-1.5 text-sm font-semibold text-emerald-700">{pass}</p>
                    {when && <p className="mt-0.5 text-sm font-medium text-neutral-600">{when}</p>}
                </div>
            </div>

            <div className="bg-neutral-50 px-5 pb-5 pt-3">
                <div
                    className={`mx-auto flex max-w-[17rem] flex-col items-center rounded-2xl border border-neutral-200 bg-white px-4 py-7 text-center ${isVoid ? 'opacity-45' : ''}`}
                >
                    <ScanLine className="mb-3 h-9 w-9 text-emerald-600" aria-hidden="true" />
                    <p className="text-sm font-semibold text-neutral-900">QR code d&apos;entrée</p>
                    <p className="mt-2 text-xs leading-relaxed text-neutral-600">
                        Téléchargez le PDF ci-dessous ou ouvrez celui reçu par e-mail. Présentez le QR du PDF à l&apos;entrée.
                    </p>
                </div>
                <p className="mt-5 text-center text-base font-bold tracking-wide text-neutral-900">{pass}</p>
                <p className="mt-1 text-center text-sm font-semibold text-neutral-700">{fullName}</p>
                {isVoid && (
                    <p className="mt-2 text-center text-sm font-semibold text-red-600">Billet {status} - entrée refusée</p>
                )}
            </div>

            <TicketPerforation notchBg={notchBgClassName} />

            <div className="bg-neutral-100 px-5 py-4 text-center">
                <p className="text-sm font-medium leading-relaxed text-neutral-700">{venueLine}</p>
            </div>

            <p className="select-all bg-neutral-100 pb-5 text-center font-mono text-xs font-semibold tracking-wide text-neutral-500">
                Identifiant · {serial}
            </p>
        </article>
    );
}
