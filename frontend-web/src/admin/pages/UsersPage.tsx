import React, { useState, useEffect } from 'react';
import { UserPlus, Trash2 } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { usersService } from '../services/users.service';
import { useEvent } from '../context/EventContext';
import { useToast } from '../context/ToastContext';
import { OrganizationMember } from '../types';
import { getAdminRoute } from '@/lib/env';

export const UsersPage: React.FC = () => {
  const { orgId } = useEvent();
  const { success, error: toastError } = useToast();
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [invites, setInvites] = useState<
    { id: string; email: string; role: string; expires_at: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'admin' | 'scanner'>('scanner');

  const loadData = async () => {
    if (!orgId) return;
    try {
      setLoading(true);
      setError(null);
      const [m, i] = await Promise.all([
        usersService.getOrgMembers(orgId),
        usersService.getInvites(orgId),
      ]);
      setMembers(m);
      setInvites(i);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Impossible de récupérer l’équipe.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [orgId]);

  const invite = async () => {
    if (!orgId || !inviteEmail.trim()) return;
    try {
      const res = await usersService.inviteMember(orgId, inviteEmail.trim(), inviteRole);
      const adminRoute = getAdminRoute() || '';
      const link = `${window.location.origin}${adminRoute}/accept-invite?token=${encodeURIComponent(res.token)}`;
      await navigator.clipboard.writeText(link);
      success('Invitation créée', 'Lien copié dans le presse-papiers.');
      setInviteEmail('');
      loadData();
    } catch (err: unknown) {
      toastError('Invitation', err instanceof Error ? err.message : 'Création impossible.');
    }
  };

  const revoke = async (inviteId: string) => {
    try {
      await usersService.revokeInvite(inviteId);
      success('Invitation révoquée', '');
      loadData();
    } catch {
      toastError('Révocation', 'Action impossible.');
    }
  };

  const changeRole = async (userId: string, role: string) => {
    if (!orgId) return;
    try {
      await usersService.updateMemberRole(orgId, userId, role);
      success('Rôle mis à jour', '');
      loadData();
    } catch {
      toastError('Rôle', 'Modification impossible.');
    }
  };

  if (!orgId) {
    return <ErrorState message="Organisation introuvable." onRetry={loadData} />;
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Équipe" subtitle="Membres, rôles et invitations staff" />

      <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm flex flex-wrap gap-3 items-end">
        <label className="flex-1 min-w-[200px] text-sm font-semibold">
          E-mail
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            placeholder="nouveau@tdev.bj"
          />
        </label>
        <label className="text-sm font-semibold">
          Rôle
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as 'admin' | 'scanner')}
            className="mt-1 block rounded-xl border border-slate-200 px-3 py-2 text-sm"
          >
            <option value="scanner">Scanner</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button
          type="button"
          onClick={invite}
          className="inline-flex items-center gap-2 rounded-xl bg-green-800 px-4 py-2.5 text-sm font-bold text-white"
        >
          <UserPlus className="h-4 w-4" />
          Inviter
        </button>
      </div>

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : (
        <>
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b bg-slate-50 text-slate-500 uppercase tracking-wider text-[11px]">
                  <th className="py-3 px-6">Membre</th>
                  <th className="py-3 px-6">E-mail</th>
                  <th className="py-3 px-6">Rôle</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {members.map((m) => (
                  <tr key={m.user_id}>
                    <td className="py-3 px-6 font-semibold">{m.user?.name}</td>
                    <td className="py-3 px-6">{m.user?.email}</td>
                    <td className="py-3 px-6">
                      <select
                        value={m.role}
                        onChange={(e) => changeRole(m.user_id, e.target.value)}
                        className="rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold"
                      >
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="scanner">Scanner</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {members.length === 0 && <EmptyState title="Aucun membre." />}
          </div>

          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            <p className="px-6 py-4 text-sm font-bold text-slate-800 border-b">Invitations en attente</p>
            {invites.length === 0 ? (
              <p className="p-6 text-sm text-slate-500">Aucune invitation.</p>
            ) : (
              <ul className="divide-y">
                {invites.map((inv) => (
                  <li key={inv.id} className="flex items-center justify-between gap-4 px-6 py-3 text-sm">
                    <div>
                      <p className="font-semibold">{inv.email}</p>
                      <p className="text-xs text-slate-500">
                        {inv.role} · expire {inv.expires_at}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => revoke(inv.id)}
                      className="text-rose-600 hover:bg-rose-50 p-2 rounded-lg"
                      title="Révoquer"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
};
