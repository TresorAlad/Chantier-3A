import { apiFetch } from './api';
import { OutboundEmail } from '../types';

export const emailsService = {
  async getAll(): Promise<OutboundEmail[]> {
    try {
      return await apiFetch<OutboundEmail[]>('/outbound-emails');
    } catch {
      return [];
    }
  },
};
