import React, { useState, useEffect } from 'react';
import {
  Users as UsersIcon,
  Shield,
  Building2,
  Mail,
  UserPlus,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { usersService } from '../services/users.service';
import { formatDateTime } from '../lib/utils';
import { OrganizationMember } from '../types';

export const UsersPage: React.FC = () => {
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await usersService.getOrgMembers();
      setMembers(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les membres.');
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
        title="Utilisateurs & Équipe d'Organisation"
        subtitle="Gestion des accès administratifs, opérateurs de scan et fondateurs"
      />

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/75 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3.5 px-6">Utilisateur</th>
                  <th className="py-3.5 px-6">Email</th>
                  <th className="py-3.5 px-6">Rôle dans l'Organisation</th>
                  <th className="py-3.5 px-6">Statut Compte</th>
                  <th className="py-3.5 px-6 text-right">Membre Depuis</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                {members.map((m, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-full bg-violet-100 text-violet-700 font-bold flex items-center justify-center text-xs">
                          {m.user?.name ? m.user.name.charAt(0).toUpperCase() : 'U'}
                        </div>
                        <span className="font-bold text-slate-900">{m.user?.name}</span>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-slate-600 font-medium">
                      {m.user?.email}
                    </td>
                    <td className="py-4 px-6">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                          m.role === 'owner'
                            ? 'bg-purple-100 text-purple-700 border border-purple-200'
                            : m.role === 'admin'
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        <Shield className="w-3 h-3" />
                        {m.role}
                      </span>
                    </td>
                    <td className="py-4 px-6">
                      <span className="inline-flex items-center gap-1 text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 text-[11px]">
                        Actif
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right text-slate-500">
                      {formatDateTime(m.created_at)}
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
