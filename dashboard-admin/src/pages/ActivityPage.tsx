import React, { useState, useEffect } from 'react';
import {
  Clock,
  Activity,
  ShoppingCart,
  QrCode,
  DollarSign,
  RefreshCw,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { activityService } from '../services/activity.service';
import { formatDateTime, formatRelativeTime } from '../lib/utils';
import { EventLog } from '../types';

export const ActivityPage: React.FC = () => {
  const [logs, setLogs] = useState<EventLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await activityService.getLogs();
      setLogs(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer le journal.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getActionIcon = (action: string) => {
    if (action.includes('ORDER')) return <ShoppingCart className="w-4 h-4 text-violet-600" />;
    if (action.includes('SCAN')) return <QrCode className="w-4 h-4 text-emerald-600" />;
    if (action.includes('PAYOUT')) return <DollarSign className="w-4 h-4 text-amber-600" />;
    return <RefreshCw className="w-4 h-4 text-blue-600" />;
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Journal d’Activité Système (Audit Log)"
        subtitle="Chronologie des opérations, événements de vente et activités de compostage"
      />

      {loading ? (
        <TableSkeleton rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : logs.length === 0 ? (
        <EmptyState title="Aucune activité récente." />
      ) : (
        <div className="bg-white p-6 sm:p-8 rounded-2xl border border-slate-100 shadow-sm">
          <div className="relative border-l-2 border-slate-100 ml-4 pl-6 space-y-8">
            {logs.map((log) => (
              <div key={log.id} className="relative group">
                {/* Node icon on timeline */}
                <div className="absolute -left-[35px] top-0 w-8 h-8 rounded-full bg-white border-2 border-violet-500 flex items-center justify-center shadow-sm">
                  {getActionIcon(log.action)}
                </div>

                <div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-violet-700 bg-violet-50 px-2 py-0.5 rounded border border-violet-100">
                      {log.action}
                    </span>
                    <span className="text-xs text-slate-400">
                      {formatDateTime(log.created_at)} ({formatRelativeTime(log.created_at)})
                    </span>
                  </div>

                  <p className="text-xs sm:text-sm text-slate-700 font-medium mt-2 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100/80">
                    {log.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
