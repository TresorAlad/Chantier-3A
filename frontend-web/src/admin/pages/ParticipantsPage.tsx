import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  Search,
  Filter,
  Download,
  Eye,
  FileSpreadsheet,
  CheckCircle2,
  XCircle,
  ExternalLink,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { participantsService } from '../services/participants.service';
import { exportsService } from '../services/exports.service';
import { useToast } from '../context/ToastContext';
import { useEvent } from '../context/EventContext';
import { formatMoney, formatDateTime } from '../lib/utils';
import { Participant } from '../types';

export const ParticipantsPage: React.FC = () => {
  const { eventId } = useEvent();
  const navigate = useNavigate();
  const { success } = useToast();

  const [participants, setParticipants] = useState<Participant[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtres
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all');
  const [nexusFilter, setNexusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const limit = 10;

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await participantsService.getAll({
        search: searchTerm,
        status: statusFilter,
        pass_tier: tierFilter,
        nexus: nexusFilter === 'all' ? undefined : nexusFilter === 'yes',
        page,
        limit,
      }, eventId);
      setParticipants(res.data);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Erreur lors de la récupération des participants.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [searchTerm, statusFilter, tierFilter, nexusFilter, page, eventId]);

  const handleExportCsv = async () => {
    await exportsService.exportParticipants(eventId);
    success('Export CSV réussi', 'Le fichier CSV des participants a été téléchargé.');
  };

  const handleExportExcel = async () => {
    await exportsService.exportParticipants(eventId);
    success('Export Excel réussi', 'Le fichier Excel a été généré.');
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gestion des Participants"
        subtitle="Consultez, filtrez et exportez la liste complète des festivaliers inscrits"
      >
        <button
          onClick={handleExportCsv}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-all"
        >
          <Download className="w-4 h-4 text-slate-500" />
          Exporter CSV
        </button>

        <button
          onClick={handleExportExcel}
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold shadow-sm transition-all"
        >
          <FileSpreadsheet className="w-4 h-4" />
          Exporter Excel
        </button>
      </PageHeader>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-[260px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Rechercher par nom, prénom, email, école..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all"
            />
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2">
          {/* Statut Paiement */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          >
            <option value="all">Tous statuts</option>
            <option value="paid">Payé</option>
            <option value="pending">En attente</option>
            <option value="refunded">Remboursé</option>
            <option value="failed">Échoué</option>
          </select>

          {/* Niveau de pass */}
          <select
            value={tierFilter}
            onChange={(e) => {
              setTierFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          >
            <option value="all">Tous les passes</option>
            <option value="standard">Standard</option>
            <option value="vip">VIP</option>
            <option value="student">Étudiant</option>
          </select>

          {/* Nexus Night */}
          <select
            value={nexusFilter}
            onChange={(e) => {
              setNexusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500"
          >
            <option value="all">Nexus Night (Tous)</option>
            <option value="yes">Avec Nexus</option>
            <option value="no">Sans Nexus</option>
          </select>

        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <TableSkeleton rows={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : participants.length === 0 ? (
        <EmptyState
          title="Aucun participant trouvé"
          description="Essayez de modifier vos filtres ou termes de recherche pour afficher les festivaliers."
          actionText="Réinitialiser les filtres"
          onAction={() => {
            setSearchTerm('');
            setStatusFilter('all');
            setTierFilter('all');
            setNexusFilter('all');
          }}
        />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-5">Participant</th>
                  <th className="py-3.5 px-5">École / Univ</th>
                  <th className="py-3.5 px-5">Billet & Série</th>
                  <th className="py-3.5 px-5">Statut</th>
                  <th className="py-3.5 px-5">Montant</th>
                  <th className="py-3.5 px-5">Date</th>
                  <th className="py-3.5 px-5 text-center">Nexus Night</th>
                  <th className="py-3.5 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {participants.map((p) => (
                  <tr
                    key={p.id}
                    className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                    onClick={() => navigate(`/participants/${p.id}`)}
                  >
                    <td className="py-4 px-5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-violet-100 text-violet-700 font-bold flex items-center justify-center text-xs shrink-0">
                          {p.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <span className="font-bold text-slate-900 block group-hover:text-violet-600 transition-colors">
                            {p.name}
                          </span>
                          <span className="text-[11px] text-slate-400">{p.email}</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-4 px-5 text-slate-600 font-medium">
                      {p.school || 'Autodidacte'}
                    </td>

                    <td className="py-4 px-5">
                      <span className="font-bold text-slate-900 block">{p.pass_name}</span>
                      <span className="text-[11px] font-mono text-slate-400">{p.serial}</span>
                    </td>

                    <td className="py-4 px-5">
                      <StatusBadge status={p.order_status} type="order" />
                    </td>

                    <td className="py-4 px-5 font-bold text-slate-900">
                      {formatMoney(p.amount_minor, p.currency)}
                    </td>

                    <td className="py-4 px-5 text-slate-500">
                      {formatDateTime(p.issued_at)}
                    </td>

                    <td className="py-4 px-5 text-center">
                      {p.is_nexus ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-pink-50 text-pink-700 border border-pink-200">
                          <CheckCircle2 className="w-3 h-3 text-pink-600" /> Oui
                        </span>
                      ) : (
                        <span className="text-slate-300 text-xs">—</span>
                      )}
                    </td>


                    <td className="py-4 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => navigate(`/participants/${p.id}`)}
                          className="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-slate-100 rounded-lg transition-colors"
                          title="Consulter le profil"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => navigate(`/orders/${p.order_id}`)}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors"
                          title="Voir la commande"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div>
              Affichage {(page - 1) * limit + 1} à {Math.min(page * limit, total)} sur {total} festivaliers
            </div>

            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Précédent
              </button>
              <span className="px-3 py-1.5 font-bold text-violet-600 bg-violet-50 rounded-lg">
                Page {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages || totalPages === 0}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Suivant
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
