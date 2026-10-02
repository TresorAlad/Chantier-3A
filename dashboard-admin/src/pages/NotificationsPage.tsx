import React, { useState, useEffect } from 'react';
import {
  Bell,
  CheckCheck,
  Check,
  Clock,
  Sparkles,
  Ticket,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { notificationsService } from '../services/notifications.service';
import { useToast } from '../context/ToastContext';
import { formatDateTime, formatRelativeTime } from '../lib/utils';
import { Notification } from '../types';

export const NotificationsPage: React.FC = () => {
  const { success } = useToast();
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await notificationsService.getAll();
      setNotifs(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de charger les notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleMarkAll = async () => {
    await notificationsService.markAllAsRead();
    success('Succès', 'Toutes les notifications ont été marquées comme lues.');
    loadData();
  };

  const handleMarkOne = async (id: string) => {
    await notificationsService.markAsRead(id);
    loadData();
  };

  const unreadCount = notifs.filter((n) => n.unread).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Centre de Notifications"
        subtitle="Alertes système, franchissement des seuils de quota et rapports"
      >
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAll}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-sm transition-all"
          >
            <CheckCheck className="w-4 h-4 text-violet-600" />
            Tout marquer comme lu
          </button>
        )}
      </PageHeader>

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : notifs.length === 0 ? (
        <EmptyState title="Aucune notification pour le moment." />
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-100 overflow-hidden">
          {notifs.map((n) => (
            <div
              key={n.id}
              className={`p-5 flex items-start justify-between gap-4 transition-colors ${
                n.unread ? 'bg-violet-50/30' : 'hover:bg-slate-50'
              }`}
            >
              <div className="flex items-start gap-3.5">
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                    n.unread
                      ? 'bg-violet-600 text-white shadow-md shadow-violet-500/20'
                      : 'bg-slate-100 text-slate-500'
                  }`}
                >
                  <Bell className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-900">{n.title}</h4>
                    {n.unread && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-violet-100 text-violet-700">
                        Nouveau
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{n.message}</p>
                  <span className="text-[11px] text-slate-400 mt-2 block">
                    {formatDateTime(n.created_at)} ({formatRelativeTime(n.created_at)})
                  </span>
                </div>
              </div>

              {n.unread && (
                <button
                  onClick={() => handleMarkOne(n.id)}
                  className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-violet-600 hover:bg-slate-100 text-xs shrink-0 transition-colors"
                  title="Marquer comme lu"
                >
                  <Check className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
