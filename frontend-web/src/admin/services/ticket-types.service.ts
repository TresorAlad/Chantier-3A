import { apiFetch } from './api';
import { TicketType } from '../types';
import { requireEventId } from '../context/EventContext';

export const ticketTypesService = {
  async getAll(eventId?: string | null): Promise<TicketType[]> {
    const id = requireEventId(eventId ?? null);
    const res = await apiFetch<{ ticket_types: TicketType[] }>(`/events/${id}/ticket-types`);
    return res.ticket_types || [];
  },

  async getGoodies(eventId?: string | null): Promise<TicketType[]> {
    const all = await this.getAll(eventId);
    return all.filter((tt) => tt.product_kind === 'goodie');
  },

  async create(eventId: string, body: Partial<TicketType>): Promise<TicketType> {
    const res = await apiFetch<{ ticket_type: TicketType }>(`/events/${eventId}/ticket-types`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
    return res.ticket_type;
  },

  async update(ttId: string, body: Partial<TicketType>): Promise<TicketType> {
    const res = await apiFetch<{ ticket_type: TicketType }>(`/ticket-types/${ttId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
    return res.ticket_type;
  },

  async remove(ttId: string): Promise<void> {
    await apiFetch<void>(`/ticket-types/${ttId}`, { method: 'DELETE' });
  },
};
