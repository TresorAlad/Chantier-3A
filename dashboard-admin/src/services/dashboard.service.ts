import { apiFetch } from './api';
import { DashboardKPIData } from '../types';

export const dashboardService = {
  async getKPIs(): Promise<DashboardKPIData> {
    return apiFetch<DashboardKPIData>('/dashboard/stats');
  },

  async getSalesChart(period = 'week'): Promise<any> {
    try {
      return await apiFetch<any>(`/analytics/registrations?period=${period}`);
    } catch {
      return [];
    }
  },

  async getTicketDistribution(): Promise<any> {
    try {
      return await apiFetch<any>('/analytics/tickets-distribution');
    } catch {
      return [];
    }
  },

  async getAdmissionStats(): Promise<Array<{ name: string; count: number; fill: string }>> {
    try {
      const admissions = await apiFetch<any[]>('/admissions');

      const stats = {
        admitted: 0,
        duplicate: 0,
        invalid: 0,
        wrong_event: 0,
      };

      admissions.forEach((admission) => {
        const result = String(admission.result || '').toLowerCase();

        if (result === 'admitted') {
          stats.admitted++;
        } else if (result === 'duplicate') {
          stats.duplicate++;
        } else if (result === 'invalid') {
          stats.invalid++;
        } else if (result === 'wrong_event') {
          stats.wrong_event++;
        }
      });

      return [
        { name: 'Admis', count: stats.admitted, fill: '#16a34a' },
        { name: 'Doublons', count: stats.duplicate, fill: '#f59e0b' },
        { name: 'Invalides', count: stats.invalid, fill: '#ef4444' },
        { name: 'Autre événement', count: stats.wrong_event, fill: '#8b5cf6' },
      ];
    } catch {
      return [];
    }
  },
};