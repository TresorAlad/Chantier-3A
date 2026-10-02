import { apiFetch } from './api';
import { Participant, OrderStatus, PassTier } from '../types';
import { requireEventId } from '../context/EventContext';

export interface ParticipantFilterParams {
  search?: string;
  status?: string;
  pass_tier?: string;
  nexus?: boolean;
  goodies?: boolean;
  page?: number;
  limit?: number;
}

function isNexusName(name: string): boolean {
  const n = name.toLowerCase();
  return n.includes('nexus') || n.includes('vip');
}

export const participantsService = {
  async getAll(
    params: ParticipantFilterParams = {},
    eventId?: string | null,
  ): Promise<{ data: Participant[]; total: number }> {
    const id = requireEventId(eventId ?? null);
    const [attendeesRes, ordersRes] = await Promise.all([
      apiFetch<{ attendees: Record<string, unknown>[] }>(`/events/${id}/attendees`),
      apiFetch<{ orders: Record<string, unknown>[] }>(`/events/${id}/orders`),
    ]);

    const orderById = new Map(
      (ordersRes.orders || []).map((o) => [String(o.id), o as Record<string, unknown>]),
    );

    let participants: Participant[] = (attendeesRes.attendees || []).map((a) => {
      const order = orderById.get(String(a.order_id)) || {};
      const reg = (order.registration as Record<string, string>) || {};
      const passName = String(a.ticket_type_name || a.pass_type || 'Pass Festival');
      return {
        id: String(a.ticket_id),
        ticket_id: String(a.ticket_id),
        order_id: String(a.order_id),
        name:
          String(a.holder_name || '').trim() ||
          `${reg.first_name || a.first_name || ''} ${reg.last_name || a.last_name || ''}`.trim() ||
          String(order.buyer_name || ''),
        first_name: String(reg.first_name || a.first_name || ''),
        last_name: String(reg.last_name || a.last_name || ''),
        email: String(a.email || order.buyer_email || reg.email || ''),
        school: String(reg.school_name || a.school_name || ''),
        serial: String(a.serial || ''),
        pass_name: passName,
        pass_tier: ((a.pass_type as string) || null) as PassTier | null,
        order_status: String(order.status || '') as OrderStatus,
        amount_minor: Number(order.total_minor || 0),
        currency: String(order.currency || 'XOF'),
        issued_at: String(a.scanned_at || order.created_at || ''),
        is_nexus: isNexusName(passName),
        has_goodies: passName.toLowerCase().includes('goodies') || passName.toLowerCase().includes('welcome'),
        goodies_details: undefined,
        admitted: Boolean(a.admitted),
      } as Participant;
    });

    if (params.search) {
      const q = params.search.toLowerCase();
      participants = participants.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.email.toLowerCase().includes(q) ||
          p.school.toLowerCase().includes(q) ||
          p.serial.toLowerCase().includes(q),
      );
    }
    if (params.status && params.status !== 'all') {
      participants = participants.filter((p) => p.order_status === params.status);
    }
    if (params.pass_tier && params.pass_tier !== 'all') {
      participants = participants.filter((p) => p.pass_tier === params.pass_tier);
    }
    if (params.nexus !== undefined) {
      participants = participants.filter((p) => p.is_nexus === params.nexus);
    }

    const total = participants.length;
    const page = params.page || 1;
    const limit = params.limit || 10;
    const data = participants.slice((page - 1) * limit, page * limit);
    return { data, total };
  },

  async getById(participantId: string, eventId?: string | null): Promise<Participant | null> {
    const all = await this.getAll({ limit: 10000 }, eventId);
    return all.data.find((p) => p.id === participantId || p.order_id === participantId) || null;
  },
};
