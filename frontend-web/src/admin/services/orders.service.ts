import { apiFetch } from './api';
import { Order, OrderStatus } from '../types';
import { requireEventId } from '../context/EventContext';

export interface OrderFilterParams {
  search?: string;
  status?: OrderStatus | 'all';
  page?: number;
  limit?: number;
}

export const ordersService = {
  async getAll(
    params: OrderFilterParams = {},
    eventId?: string | null,
  ): Promise<{ data: Order[]; total: number }> {
    const id = requireEventId(eventId ?? null);
    const res = await apiFetch<{ orders: Order[] }>(`/events/${id}/orders`);
    let orders = res.orders || [];

    if (params.search) {
      const q = params.search.toLowerCase();
      orders = orders.filter(
        (o) =>
          o.buyer_email?.toLowerCase().includes(q) ||
          o.buyer_name?.toLowerCase().includes(q) ||
          o.id?.toLowerCase().includes(q),
      );
    }
    if (params.status && params.status !== 'all') {
      orders = orders.filter((o) => o.status === params.status);
    }

    const total = orders.length;
    const page = params.page || 1;
    const limit = params.limit || 20;
    const data = orders.slice((page - 1) * limit, page * limit);
    return { data, total };
  },

  async getById(id: string): Promise<Order | null> {
    try {
      const res = await apiFetch<{ order: Order & { tickets?: unknown[] } }>(`/orders/${id}`);
      return res.order || null;
    } catch {
      return null;
    }
  },

  async markPaid(orderId: string): Promise<{ order: Order; tickets: unknown[] }> {
    return apiFetch(`/orders/${orderId}/mark-paid`, { method: 'POST' });
  },

  async markFailed(orderId: string): Promise<{ order: Order }> {
    return apiFetch(`/orders/${orderId}/mark-failed`, { method: 'POST' });
  },
};
