import React, { useState, useEffect } from 'react';
import {
  CreditCard,
  Search,
  Download,
  Filter,
  CheckCircle2,
  Clock,
  RefreshCw,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { paymentsService } from '../services/payments.service';
import { exportToCsv } from '../lib/export';
import { useToast } from '../context/ToastContext';
import { formatMoney, formatDateTime } from '../lib/utils';
import { PaymentRecord } from '../types';

export const PaymentsPage: React.FC = () => {
  const { success } = useToast();
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await paymentsService.getAll();
      setPayments(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de charger les paiements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = payments.filter((p) => {
    const matchesSearch =
      p.reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.provider.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.instructions.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || p.status.toLowerCase() === statusFilter.toLowerCase();
    return matchesSearch && matchesStatus;
  });

  const handleExport = () => {
    const rows = filtered.map((p) => ({
      Reference: p.reference,
      Fournisseur: p.provider,
      Montant: formatMoney(p.amount_minor, p.currency),
      Statut: p.status,
      Details: p.instructions,
      Marque_Par: p.marked_by,
      Date_Creation: formatDateTime(p.created_at),
      Date_Validation: formatDateTime(p.marked_at),
    }));
    exportToCsv('tdev_paiements_export', rows);
    success('Export CSV réussi', 'Le relevé des paiements a été téléchargé.');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Journal des Paiements & Transactions"
        subtitle="Historique des paiements FedaPay, MTN Mobile Money, Moov et virements"
      >
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-all"
        >
          <Download className="w-4 h-4 text-slate-500" />
          Exporter CSV
        </button>
      </PageHeader>

      {/* Filter and search */}
      <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[260px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher par référence, fournisseur ou libellé..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
        >
          <option value="all">Tous les états</option>
          <option value="approved">Validé / Payé</option>
          <option value="pending">En attente</option>
          <option value="refunded">Remboursé</option>
        </select>
      </div>

      {loading ? (
        <TableSkeleton rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filtered.length === 0 ? (
        <EmptyState title="Aucun enregistrement de paiement trouvé." />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">Référence</th>
                  <th className="py-3.5 px-6">Passerelle</th>
                  <th className="py-3.5 px-6">Montant</th>
                  <th className="py-3.5 px-6">Instructions / Remarque</th>
                  <th className="py-3.5 px-6">Validé Par</th>
                  <th className="py-3.5 px-6">Statut</th>
                  <th className="py-3.5 px-6 text-right">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {filtered.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-6 font-mono font-bold text-violet-700">
                      {p.reference}
                    </td>
                    <td className="py-4 px-6 uppercase font-bold text-slate-800">
                      {p.provider}
                    </td>
                    <td className="py-4 px-6 font-extrabold text-slate-900">
                      {formatMoney(p.amount_minor, p.currency)}
                    </td>
                    <td className="py-4 px-6 text-slate-600 max-w-xs truncate">
                      {p.instructions || '—'}
                    </td>
                    <td className="py-4 px-6 font-mono text-[11px] text-slate-500">
                      {p.marked_by || 'webhook'}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={p.status} type="order" />
                    </td>
                    <td className="py-4 px-6 text-right text-slate-500">
                      {formatDateTime(p.created_at)}
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
