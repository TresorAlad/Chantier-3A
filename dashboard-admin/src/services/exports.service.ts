import { apiClient } from './api';

type ExportKind = 'participants' | 'tickets' | 'admissions' | 'orders';
async function download(kind: ExportKind) {
  await apiClient.download(`/admin/exports/${kind}.csv`, `tdev_${kind}.csv`);
}

/** Les exports proviennent tous de Neon via FastAPI, jamais de données locales. */
export const exportsService = {
  downloadServerCsv: (kind: ExportKind) => download(kind),
  exportParticipants: (_format: 'csv' | 'excel' = 'csv') => download('participants'),
  exportTickets: (_format: 'csv' | 'excel' = 'csv') => download('tickets'),
  exportAdmissions: (_format: 'csv' | 'excel' = 'csv') => download('admissions'),
  exportOrders: (_format: 'csv' | 'excel' = 'csv') => download('orders'),
};
