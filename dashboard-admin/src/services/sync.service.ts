import { apiFetch } from './api';
import { SyncPeer } from '../types';

export const syncService = {
  async getPeers(): Promise<SyncPeer[]> {
    try {
      return await apiFetch<SyncPeer[]>('/sync/peers');
    } catch {
      return [];
    }
  },

  async triggerSync(peerId: string): Promise<boolean> {
    try {
      await apiFetch(`/sync/peers/${peerId}/run`, { method: 'POST' });
      return true;
    } catch {
      return false;
    }
  },
};
