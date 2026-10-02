import { apiFetch } from './api';
import { Notification } from '../types';

export const notificationsService = {
  async getAll(): Promise<Notification[]> {
    try {
      return await apiFetch<Notification[]>('/notifications');
    } catch {
      return [];
    }
  },

  async markAsRead(id: string): Promise<boolean> {
    try {
      await apiFetch(`/notifications/${id}/read`, { method: 'POST' });
      return true;
    } catch {
      return false;
    }
  },

  async markAllAsRead(): Promise<boolean> {
    try {
      await apiFetch('/notifications/mark-all-read', { method: 'POST' });
      return true;
    } catch {
      return false;
    }
  },
};
