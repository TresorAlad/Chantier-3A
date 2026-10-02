import React, { useState, useEffect } from 'react';
import {
  DollarSign,
  Building2,
  Calendar,
  CheckCircle2,
  Clock,
  ArrowUpRight,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { StatCard } from '../components/ui/StatCard';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { payoutsService } from '../services/payouts.service';
import { formatMoney, formatDateTime } from '../lib/utils';
import { Payout } from '../types';

export const PayoutsPage: React.FC = () => {
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await payoutsService.getAll();
      setPayouts(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les virements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalPaid = payouts
    .filter((p) => p.status === 'paid')
    .reduce((acc, p) => acc + p.amount_minor, 0);

  const totalPending = payouts
    .filter((p) => p.status === 'processing' || p.status === 'pending')
    .reduce((acc, p) => acc + p.amount_minor, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Versements & Virements Bancaires (Payouts)"
        subtitle="Règlements des recettes billetterie vers le compte bancaire de l’organisation"
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <StatCard
          title="Total Reçu sur Compte"
          value={formatMoney(totalPaid, 'XOF')}
          icon={<DollarSign className="w-5 h-5 text-white" />}
          iconBgColor="bg-emerald-500"
          subtitle={<span className="text-slate-500">Compte BGFI Bank Bénin</span>}
        />

        <StatCard
          title="En Cours de Traitement"
          value={formatMoney(totalPending, 'XOF')}
          icon={<Clock className="w-5 h-5 text-white" />}
          iconBgColor="bg-amber-500"
          subtitle={<span className="text-slate-500">Délai interbancaire 24h-48h</span>}
        />
      </div>

      {loading ? (
        <TableSkeleton rows={2} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : payouts.length === 0 ? (
        <EmptyState title="Aucun virement enregistré." />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">ID Virement</th>
                  <th className="py-3.5 px-6">Événement Associé</th>
                  <th className="py-3.5 px-6">Montant Viré</th>
                  <th className="py-3.5 px-6">Réf Banque / Fournisseur</th>
                  <th className="py-3.5 px-6">Statut</th>
                  <th className="py-3.5 px-6">Demandé le</th>
                  <th className="py-3.5 px-6 text-right">Date Rapprochement</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {payouts.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-6 font-mono font-bold text-violet-700">
                      {p.id}
                    </td>
                    <td className="py-4 px-6 font-semibold text-slate-900">
                      {p.event_title || 'TDEV Festival 2026'}
                    </td>
                    <td className="py-4 px-6 font-extrabold text-slate-900">
                      {formatMoney(p.amount_minor, p.currency)}
                    </td>
                    <td className="py-4 px-6 font-mono text-[11px] text-slate-600">
                      {p.provider_ref || '—'}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={p.status} type="order" />
                    </td>
                    <td className="py-4 px-6 text-slate-500">
                      {formatDateTime(p.created_at)}
                    </td>
                    <td className="py-4 px-6 text-right text-slate-500 font-medium">
                      {formatDateTime(p.paid_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
