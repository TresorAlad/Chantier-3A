import { apiFetch } from './api';
import { Event } from '../types';
import { requireEventId } from '../context/EventContext';

export const eventsService = {
  async getById(idOrSlug: string): Promise<Event | null> {
    try {
      const res = await apiFetch<{ event: Event }>(`/events/${idOrSlug}`);
      return res.event;
    } catch {
      return null;
    }
  },

  async getCurrent(eventId?: string | null): Promise<Event | null> {
    const id = requireEventId(eventId ?? null);
    return this.getById(id);
  },

  async update(eventId: string, body: Partial<Event>): Promise<Event> {
    const res = await apiFetch<{ event: Event }>(`/events/${eventId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
    return res.event;
  },

  async publish(eventId: string): Promise<Event> {
    const res = await apiFetch<{ event: Event }>(`/events/${eventId}/publish`, {
      method: 'POST',
    });
    return res.event;
  },
};
