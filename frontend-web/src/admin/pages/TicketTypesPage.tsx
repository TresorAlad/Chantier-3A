import React, { useState, useEffect } from 'react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { ticketTypesService } from '../services/ticket-types.service';
import { formatMoney } from '../lib/utils';
import { formatCatalogTicketTypes, type TicketTypeDisplay } from '../lib/ticket-type-catalog-display';
import { useEvent } from '../context/EventContext';
import { adminTheme } from '../lib/admin-theme';
import { cn } from '../lib/utils';
import { WELCOME_PACK_SHOP_URL } from '@/lib/static-billetterie-catalog';
import { ExternalLink } from 'lucide-react';

function CatalogCard({ row }: { row: TicketTypeDisplay }) {
  const { ticket, displayTitle, displayDescription, categoryLabel, gauge } = row;
  const isGoodie = ticket.product_kind === 'goodie';

  return (
    <article className={cn(adminTheme.cardInteractive, 'flex flex-col justify-between p-5')}>
      <div>
        <div className="mb-3 flex items-start justify-between gap-3">
          <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-600">
            {categoryLabel}
          </span>
          <span className="text-lg font-semibold tabular-nums text-zinc-900">
            {formatMoney(ticket.price_minor, 'XOF')}
          </span>
        </div>

        <h3 className="text-base font-semibold tracking-tight text-zinc-900">{displayTitle}</h3>
        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-zinc-500">{displayDescription}</p>
      </div>

      {isGoodie ? (
        <div className="mt-6 border-t border-zinc-100 pt-4">
          <a
            href={WELCOME_PACK_SHOP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className={cn('inline-flex items-center gap-1 text-xs', adminTheme.linkAccent)}
          >
            Ouvrir la boutique merch
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      ) : (
        <div className="mt-6 space-y-3 border-t border-zinc-100 pt-4">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-zinc-500">Ventes</span>
            <span className="font-semibold tabular-nums text-zinc-900">
              {gauge.soldLabel}
              {!gauge.unlimitedQuota && (
                <span className="ml-1 font-normal text-zinc-500">({gauge.percentLabel})</span>
              )}
              {gauge.unlimitedQuota && (
                <span className="ml-1 font-normal text-zinc-500">· {gauge.percentLabel}</span>
              )}
            </span>
          </div>

          <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
            <div
              className={cn(
                'h-full rounded-full bg-emerald-600 transition-all duration-500',
                gauge.unlimitedQuota && 'bg-emerald-500/70',
                gauge.barWidth >= 90 && !gauge.unlimitedQuota && 'bg-amber-600',
              )}
              style={{ width: `${gauge.barWidth}%` }}
            />
          </div>

          <div className="flex items-center justify-between pt-1 text-xs text-zinc-500">
            <span>
              Places restantes :{' '}
              <strong className="text-zinc-800">{gauge.remainingLabel}</strong>
            </span>
            <span>
              Max. par commande :{' '}
              <strong className="text-zinc-800">{ticket.max_per_order}</strong>
            </span>
          </div>
        </div>
      )}
    </article>
  );
}

export const TicketTypesPage: React.FC = () => {
  const { eventId } = useEvent();
  const [rows, setRows] = useState<TicketTypeDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ticketTypesService.getAll(eventId);
      setRows(formatCatalogTicketTypes(data));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Impossible de charger les passes.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [eventId]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Catalogue des passes"
        subtitle="Pass Festival, Nexus Night et Welcome Pack tels que présentés aux visiteurs"
      />

      {loading ? (
        <TableSkeleton rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Aucun pass configuré"
          description="Les offres du festival s’afficheront ici dès qu’elles seront disponibles."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <CatalogCard key={row.ticket.id} row={row} />
          ))}
        </div>
      )}
    </div>
  );
};
