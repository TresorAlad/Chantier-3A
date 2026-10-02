import { apiFetch } from './api';
import { Ticket, TicketStatus } from '../types';

export const ticketsService = {
  async getAll(params: { status?: TicketStatus | 'all'; search?: string } = {}): Promise<Ticket[]> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status && params.status !== 'all') query.append('status', params.status);

    try {
      return await apiFetch<Ticket[]>(`/tickets?${query.toString()}`);
    } catch {
      return [];
    }
  },

  async voidTicket(serial: string): Promise<boolean> {
    try {
      await apiFetch(`/tickets/${serial}/void`, { method: 'POST' });
      return true;
    } catch {
      return false;
    }
  },
};
