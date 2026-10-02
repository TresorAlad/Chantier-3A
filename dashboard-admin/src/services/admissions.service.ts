import { apiFetch } from './api';
import { Admission, AdmissionResult } from '../types';

export const admissionsService = {
  async getAll(params: { result?: AdmissionResult | 'all'; search?: string } = {}): Promise<Admission[]> {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.result && params.result !== 'all') query.append('result', params.result);

    return apiFetch<Admission[]>(`/admissions?${query.toString()}`);
  },
};
