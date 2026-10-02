import { apiFetch, apiClient, API_URL } from './api';
import { Ticket, TicketStatus } from '../types';
import { requireEventId } from '../context/EventContext';

export const ticketsService = {
  async getAll(
    params: { status?: TicketStatus | 'all'; search?: string } = {},
    eventId?: string | null,
  ): Promise<Ticket[]> {
    const id = requireEventId(eventId ?? null);
    const res = await apiFetch<{ attendees: Record<string, unknown>[] }>(`/events/${id}/attendees`);
    let attendees = (res.attendees || []).map((a) => ({
      id: String(a.ticket_id),
      order_id: String(a.order_id),
      event_id: id,
      ticket_type_id: String(a.ticket_type_id),
      holder_name: String(a.holder_name || `${a.first_name} ${a.last_name}`.trim()),
      serial: String(a.serial),
      capability: '',
      status: (a.status as TicketStatus) || 'valid',
      issued_at: String(a.admitted_at || ''),
      ticket_type: {
        id: String(a.ticket_type_id),
        name: String(a.ticket_type_name || a.pass_type || 'Pass Festival'),
        pass_tier: a.pass_type as string,
        product_kind: 'ticket',
        event_id: id,
        description: '',
        price_minor: 0,
        quantity_total: 0,
        quantity_sold: 0,
        max_per_order: 1,
        sort_order: 0,
        status: 'active',
      },
      buyer_email: String(a.email || ''),
      admitted: Boolean(a.admitted),
    })) as (Ticket & { buyer_email?: string; admitted?: boolean })[];

    if (params.search) {
      const q = params.search.toLowerCase();
      attendees = attendees.filter(
        (t) =>
          t.serial?.toLowerCase().includes(q) ||
          t.holder_name?.toLowerCase().includes(q) ||
          (t as { buyer_email?: string }).buyer_email?.toLowerCase().includes(q),
      );
    }
    if (params.status && params.status !== 'all') {
      attendees = attendees.filter((t) => t.status === params.status);
    }
    return attendees;
  },

  async downloadPdf(ticketId: string): Promise<void> {
    const token = apiClient.getToken();
    const response = await fetch(`${API_URL}/tickets/${ticketId}/pdf`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error('PDF indisponible');
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `billet-${ticketId}.pdf`;
    link.click();
    URL.revokeObjectURL(objectUrl);
  },

  async resendEmail(ticketId: string): Promise<void> {
    await apiFetch(`/tickets/${ticketId}/resend`, { method: 'POST' });
  },
};
