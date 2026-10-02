import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Order, OrderStatus } from '../../types';
import { formatMoney, formatDateTime } from '../../lib/utils';
import { StatusBadge } from '../ui/StatusBadge';
import { Search, Eye, MoreVertical, ChevronLeft, ChevronRight } from 'lucide-react';

interface RecentOrdersTableProps {
  orders: Order[];
}

export const RecentOrdersTable: React.FC<RecentOrdersTableProps> = ({ orders }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<OrderStatus | 'all'>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;
  const navigate = useNavigate();

  const filtered = orders.filter((o) => {
    const matchesSearch =
      o.buyer_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.buyer_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      o.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'all' || o.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalPages = Math.ceil(filtered.length / itemsPerPage) || 1;
  const paginated = filtered.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      {/* Table Header with Search & Filter */}
      <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Commandes Récentes
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Flux des dernières inscriptions et paiements en direct
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="pl-9 pr-3.5 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all w-40 sm:w-56"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as any);
              setCurrentPage(1);
            }}
            className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all"
          >
            <option value="all">Tous les statuts</option>
            <option value="paid">Payé</option>
            <option value="pending">En attente</option>
            <option value="failed">Échoué</option>
            <option value="refunded">Remboursé</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
              <th className="py-3.5 px-6">Participant / Acheteur</th>
              <th className="py-3.5 px-6">École / Organisation</th>
              <th className="py-3.5 px-6">Montant</th>
              <th className="py-3.5 px-6">Date</th>
              <th className="py-3.5 px-6">Statut</th>
              <th className="py-3.5 px-6 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
            {paginated.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400">
                  Aucune commande ne correspond aux critères.
                </td>
              </tr>
            ) : (
              paginated.map((order) => (
                <tr
                  key={order.id}
                  className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                  onClick={() => navigate(`/orders/${order.id}`)}
                >
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-violet-100 text-violet-700 font-bold flex items-center justify-center text-xs shrink-0">
                        {order.buyer_name ? order.buyer_name.charAt(0).toUpperCase() : 'U'}
                      </div>
                      <div>
                        <span className="font-bold text-slate-900 block group-hover:text-violet-600 transition-colors">
                          {order.buyer_name || 'Anonyme'}
                        </span>
                        <span className="text-[11px] text-slate-400">{order.buyer_email}</span>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-6 text-slate-600 font-medium">
                    {order.school_name || 'Non renseigné'}
                  </td>
                  <td className="py-4 px-6 font-bold text-slate-900">
                    {formatMoney(order.total_minor, order.currency)}
                  </td>
                  <td className="py-4 px-6 text-slate-500">
                    {formatDateTime(order.created_at)}
                  </td>
                  <td className="py-4 px-6">
                    <StatusBadge status={order.status} type="order" />
                  </td>
                  <td className="py-4 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => navigate(`/orders/${order.id}`)}
                        className="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-slate-100 rounded-lg transition-colors"
                        title="Voir le détail"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                        title="Options"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
        <div>
          Affichage {paginated.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0} à{' '}
          {Math.min(currentPage * itemsPerPage, filtered.length)} sur {filtered.length} commandes
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {Array.from({ length: totalPages }).map((_, i) => (
            <button
              key={i + 1}
              onClick={() => setCurrentPage(i + 1)}
              className={`w-7 h-7 rounded-lg text-xs font-semibold transition-all ${
                currentPage === i + 1
                  ? 'bg-violet-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {i + 1}
            </button>
          ))}

          <button
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages || totalPages === 0}
            className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
