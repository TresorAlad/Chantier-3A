import React, { useState, useEffect } from 'react';
import {
  Tags,
  Plus,
  TrendingUp,
  Package,
  Layers,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { ticketTypesService } from '../services/ticket-types.service';
import { formatMoney } from '../lib/utils';
import { TicketType } from '../types';

export const TicketTypesPage: React.FC = () => {
  const [types, setTypes] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ticketTypesService.getAll();
      setTypes(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les types de billets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Catalogue des Types de Billets & Produits"
        subtitle="Configurez les catégories de passes, tarifs, quotas et options"
      />

      {loading ? (
        <TableSkeleton rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {types.map((tt) => {
            const remaining = tt.quantity_total - tt.quantity_sold;
            const percent = Math.min(
              100,
              Math.round((tt.quantity_sold / (tt.quantity_total || 1)) * 100)
            );

            return (
              <div
                key={tt.id}
                className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-card-hover transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <span className="px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-violet-50 text-violet-700 border border-violet-100">
                      {tt.product_kind} {tt.pass_tier ? `• ${tt.pass_tier}` : ''}
                    </span>
                    <span className="text-lg font-black text-slate-900">
                      {formatMoney(tt.price_minor, 'XOF')}
                    </span>
                  </div>

                  <h3 className="text-base font-bold text-slate-900 tracking-tight">
                    {tt.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                    {tt.description || 'Aucune description saisie.'}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Jauge Ventes</span>
                    <span className="font-extrabold text-slate-900">
                      {tt.quantity_sold} / {tt.quantity_total} ({percent}%)
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full h-2.5 rounded-full bg-slate-100 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        percent >= 90
                          ? 'bg-rose-500'
                          : percent >= 70
                          ? 'bg-violet-600'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${percent}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                    <span>Restant : <strong className="text-slate-800">{remaining}</strong></span>
                    <span>Max/commande : <strong className="text-slate-800">{tt.max_per_order}</strong></span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
