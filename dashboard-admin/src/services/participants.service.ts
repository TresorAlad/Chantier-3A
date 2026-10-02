import { apiFetch } from './api';
import { Participant } from '../types';

export interface ParticipantFilterParams {
  search?: string;
  status?: string;
  pass_tier?: string;
  nexus?: boolean;
  goodies?: boolean;
  page?: number;
  limit?: number;
}

export const participantsService = {
  async getAll(params: ParticipantFilterParams = {}): Promise<{ data: Participant[]; total: number }> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.status && params.status !== 'all') query.append('status', params.status);
    if (params.pass_tier && params.pass_tier !== 'all') query.append('pass_tier', params.pass_tier);
    if (params.nexus !== undefined) query.append('nexus', String(params.nexus));
    if (params.page) query.append('page', params.page.toString());
    if (params.limit) query.append('limit', params.limit.toString());
    
    return apiFetch<{ data: Participant[]; total: number }>(`/participants?${query.toString()}`);
  },

  async getById(id: string): Promise<Participant | null> {
    return apiFetch<Participant>(`/participants/${id}`);
  },
};
