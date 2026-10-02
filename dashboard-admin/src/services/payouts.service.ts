import { apiFetch } from './api';
import { Payout } from '../types';

export const payoutsService = {
  async getAll(): Promise<Payout[]> {
    try {
      return await apiFetch<Payout[]>('/payouts');
    } catch {
      return [];
    }
  },
};
