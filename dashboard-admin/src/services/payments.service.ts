import { apiFetch } from './api';
import { PaymentRecord } from '../types';

export const paymentsService = {
  async getAll(): Promise<PaymentRecord[]> {
    try {
      return await apiFetch<PaymentRecord[]>('/payments');
    } catch {
      return [];
    }
  },
};
