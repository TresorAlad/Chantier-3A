import { apiFetch } from './api';
import { TicketType } from '../types';

export const ticketTypesService = {
  async getAll(eventId?: string): Promise<TicketType[]> {
    try {
      const slug = eventId || 'tdev-festival-2026';
      return await apiFetch<TicketType[]>(`/events/${slug}/ticket-types`);
    } catch {
      return [];
    }
  },
  
  async getGoodies(eventId?: string): Promise<TicketType[]> {
    const all = await this.getAll(eventId);
    return all.filter((tt) => tt.product_kind === 'goodie');
  }
};
