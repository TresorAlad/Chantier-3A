import { exportToCsv } from '../lib/export';
import { participantsService } from './participants.service';
import { ordersService } from './orders.service';
import { ticketsService } from './tickets.service';
import { admissionsService } from './admissions.service';

type ExportKind = 'participants' | 'tickets' | 'admissions' | 'orders';

export const exportsService = {
  async exportParticipants(eventId: string | null, _format: 'csv' | 'excel' = 'csv') {
    const { data } = await participantsService.getAll({ limit: 100000 }, eventId);
    exportToCsv(
      'tdev_participants',
      data.map((p) => ({
        nom: p.name,
        email: p.email,
        ecole: p.school,
        pass: p.pass_name,
        serie: p.serial,
        statut_commande: p.order_status,
        admis: p.admitted ? 'oui' : 'non',
      })),
    );
  },

  async exportOrders(eventId: string | null, _format: 'csv' | 'excel' = 'csv') {
    const { data } = await ordersService.getAll({ limit: 100000 }, eventId);
    exportToCsv(
      'tdev_orders',
      data.map((o) => ({
        id: o.id,
        acheteur: o.buyer_name,
        email: o.buyer_email,
        statut: o.status,
        total: o.total_minor,
        devise: o.currency,
        cree_le: o.created_at,
      })),
    );
  },

  async exportTickets(eventId: string | null, _format: 'csv' | 'excel' = 'csv') {
    const data = await ticketsService.getAll({}, eventId);
    exportToCsv(
      'tdev_tickets',
      data.map((t) => ({
        serie: t.serial,
        detenteur: t.holder_name,
        statut: t.status,
        pass: t.ticket_type?.name,
        commande: t.order_id,
      })),
    );
  },

  async exportAdmissions(eventId: string | null, _format: 'csv' | 'excel' = 'csv') {
    const data = await admissionsService.getAll({}, eventId);
    exportToCsv(
      'tdev_admissions',
      data.map((a) => ({
        resultat: a.result,
        serie: a.serial,
        nom: a.holder_name,
        portique: a.gate_id,
        date: a.scanned_at,
        note: a.note,
      })),
    );
  },

  downloadServerCsv(kind: ExportKind, eventId: string | null) {
    switch (kind) {
      case 'participants':
        return this.exportParticipants(eventId);
      case 'orders':
        return this.exportOrders(eventId);
      case 'tickets':
        return this.exportTickets(eventId);
      case 'admissions':
        return this.exportAdmissions(eventId);
    }
  },
};
