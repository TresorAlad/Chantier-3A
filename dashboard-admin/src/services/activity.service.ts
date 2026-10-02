import { apiFetch } from './api';
import { EventLog } from '../types';

export const activityService = {
  async getLogs(): Promise<EventLog[]> {
    try {
      return await apiFetch<EventLog[]>('/events-log');
    } catch {
      return [];
    }
  },
};
