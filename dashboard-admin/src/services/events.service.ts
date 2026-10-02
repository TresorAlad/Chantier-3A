import { apiFetch } from './api';
import { Event } from '../types';

export const eventsService = {
  async getAll(): Promise<Event[]> {
    try {
      return await apiFetch<Event[]>('/events');
    } catch {
      return [];
    }
  },

  async getById(idOrSlug: string): Promise<Event | null> {
    try {
      return await apiFetch<Event>(`/events/${idOrSlug}`);
    } catch {
      return null;
    }
  },
};
