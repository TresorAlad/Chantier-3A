import React, { useState, useEffect } from 'react';
import {
  Mail,
  Search,
  CheckCircle2,
  Clock,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { emailsService } from '../services/emails.service';
import { formatDateTime } from '../lib/utils';
import { OutboundEmail } from '../types';

export const EmailsPage: React.FC = () => {
  const [emails, setEmails] = useState<OutboundEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await emailsService.getAll();
      setEmails(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les emails.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filtered = emails.filter(
    (e) =>
      e.to_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.template.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Suivi des Emails Transactionnels Sortants"
        subtitle="Historique des e-mails d’envoi de billets, reçus de paiement et rappels"
      />

      {/* Search */}
      <div className="bg-white p-4 rounded-2xl border border-slate-100 shadow-sm">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Rechercher par destinataire, modèle ou objet..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-slate-200 bg-slate-50 text-xs font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 transition-all"
          />
        </div>
      </div>

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : filtered.length === 0 ? (
        <EmptyState title="Aucun e-mail trouvé." />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">Destinataire</th>
                  <th className="py-3.5 px-6">Modèle / Template</th>
                  <th className="py-3.5 px-6">Objet du Message</th>
                  <th className="py-3.5 px-6">Statut Envoi</th>
                  <th className="py-3.5 px-6">Créé le</th>
                  <th className="py-3.5 px-6 text-right">Envoyé le</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {filtered.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-6 font-bold text-slate-900">
                      {m.to_email}
                    </td>
                    <td className="py-4 px-6">
                      <span className="font-mono text-[11px] bg-slate-100 px-2 py-0.5 rounded text-slate-700">
                        {m.template}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-slate-700 max-w-sm truncate">
                      {m.subject}
                    </td>
                    <td className="py-4 px-6">
                      <StatusBadge status={m.status} type="email" />
                    </td>
                    <td className="py-4 px-6 text-slate-500">
                      {formatDateTime(m.created_at)}
                    </td>
                    <td className="py-4 px-6 text-right text-slate-500 font-medium">
                      {formatDateTime(m.sent_at)}
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
