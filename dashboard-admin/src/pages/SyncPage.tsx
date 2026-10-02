import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Server,
  Key,
  Globe,
  CheckCircle2,
  AlertCircle,
  Play,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { syncService } from '../services/sync.service';
import { useToast } from '../context/ToastContext';
import { formatDateTime } from '../lib/utils';
import { SyncPeer } from '../types';

export const SyncPage: React.FC = () => {
  const { success } = useToast();
  const [peers, setPeers] = useState<SyncPeer[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await syncService.getPeers();
      setPeers(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les nœuds de réplication.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSyncNow = async (id: string) => {
    setSyncingId(id);
    await syncService.triggerSync(id);
    setSyncingId(null);
    success('Synchronisation terminée', 'Le journal d’opérations a convergé.');
    loadData();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Synchronisation du Registre Hors-ligne (Mesh Sync)"
        subtitle="Supervision de la réplication pair-à-pair du registre des admissions entre le cloud et les guichets locaux"
      />

      <div className="bg-gradient-to-r from-slate-900 to-indigo-950 text-white p-6 rounded-2xl border border-slate-800 shadow-md">
        <h3 className="text-base font-bold flex items-center gap-2 mb-2">
          <Server className="w-5 h-5 text-violet-400" />
          Architecture de Résilience Hors-Ligne
        </h3>
        <p className="text-xs text-slate-300 leading-relaxed max-w-3xl">
          Chaque point de contrôle (terminal scanner mobile ou serveur local de portique)
          conserve une copie signée en Ed25519 des billets et synchronise ses scans via des curseurs de réplication.
          Même en cas de coupure Internet sur le lieu de l’événement, les admissions continuent sans interruption.
        </p>
      </div>

      {loading ? (
        <TableSkeleton rows={2} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : peers.length === 0 ? (
        <EmptyState title="Aucun pair de synchronisation configuré." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {peers.map((peer) => (
            <div
              key={peer.id}
              className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col justify-between space-y-5"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-violet-50 text-violet-600 flex items-center justify-center shrink-0">
                    <Server className="w-5 h-5" />
                  </div>
                  <StatusBadge status={peer.last_status} type="sync" />
                </div>

                <h3 className="text-base font-bold text-slate-900">{peer.name}</h3>
                <p className="text-xs font-mono text-slate-500 mt-1 flex items-center gap-1.5 break-all">
                  <Globe className="w-3.5 h-3.5 text-slate-400 shrink-0" /> {peer.url}
                </p>

                <div className="mt-4 p-3 bg-slate-50 rounded-xl border border-slate-100 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Curseur Pull (Entrant)</span>
                    <span className="font-mono font-bold text-slate-800">{peer.pull_cursor} ops</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Curseur Push (Sortant)</span>
                    <span className="font-mono font-bold text-slate-800">{peer.push_cursor} ops</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dernière synchro</span>
                    <span className="font-medium text-slate-700">{formatDateTime(peer.last_sync_at)}</span>
                  </div>
                </div>

                <div className="mt-3">
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Clé publique Ed25519 (Pinning)
                  </span>
                  <div className="p-2 bg-slate-900 text-slate-300 font-mono text-[10px] rounded-lg truncate">
                    {peer.public_key}
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleSyncNow(peer.id)}
                disabled={syncingId === peer.id}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-semibold text-xs shadow-sm transition-all disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${syncingId === peer.id ? 'animate-spin' : ''}`} />
                {syncingId === peer.id ? 'Synchronisation en cours...' : 'Forcer la synchronisation'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
