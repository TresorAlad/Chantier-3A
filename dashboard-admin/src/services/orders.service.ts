import { apiFetch } from './api';
import { Order, OrderStatus } from '../types';

export interface OrderFilterParams {
  search?: string;
  status?: OrderStatus | 'all';
  page?: number;
  limit?: number;
}

export const ordersService = {
  async getAll(params: OrderFilterParams = {}): Promise<{ data: Order[]; total: number }> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status && params.status !== 'all') query.append('status', params.status);
    if (params.page) query.append('page', params.page.toString());
    if (params.limit) query.append('limit', params.limit.toString());

    try {
      return await apiFetch<{ data: Order[]; total: number }>(`/orders?${query.toString()}`);
    } catch {
      return { data: [], total: 0 };
    }
  },

  async getById(id: string): Promise<Order | null> {
    try {
      return await apiFetch<Order>(`/orders/${id}`);
    } catch {
      return null;
    }
  },
};
