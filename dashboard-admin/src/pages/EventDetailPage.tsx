import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Calendar,
  MapPin,
  Clock,
  Ticket,
  Users,
  ShoppingCart,
  CircleDollarSign,
  QrCode,
  Image as ImageIcon,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { StatusBadge } from '../components/ui/StatusBadge';
import { StatCard } from '../components/ui/StatCard';
import { eventsService } from '../services/events.service';
import { ticketTypesService } from '../services/ticket-types.service';
import { ordersService } from '../services/orders.service';
import { participantsService } from '../services/participants.service';
import { admissionsService } from '../services/admissions.service';
import { formatMoney, formatDateTime, formatDate } from '../lib/utils';
import { Event, TicketType, Order, Participant, Admission } from '../types';

export const EventDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [event, setEvent] = useState<Event | null>(null);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [admissions, setAdmissions] = useState<Admission[]>([]);
  const [activeTab, setActiveTab] = useState<'info' | 'tickets' | 'participants' | 'orders' | 'admissions'>('info');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      const e = await eventsService.getById(id);
      setEvent(e);
      const [tt, ord, part, adm] = await Promise.all([
        ticketTypesService.getAll(e?.id),
        ordersService.getAll({ limit: 5 }),
        participantsService.getAll({ limit: 5 }),
        admissionsService.getAll(),
      ]);
      setTicketTypes(tt);
      setOrders(ord.data);
      setParticipants(part.data);
      setAdmissions(adm);
      setLoading(false);
    }
    load();
  }, [id]);

  if (loading) return <div className="p-12 text-center text-slate-400">Chargement de l'événement...</div>;

  if (!event) {
    return (
      <div className="p-12 text-center">
        <h2 className="text-xl font-bold text-slate-800">Événement introuvable</h2>
        <button
          onClick={() => navigate('/events')}
          className="mt-4 px-4 py-2 bg-violet-600 text-white rounded-xl text-sm font-semibold"
        >
          Retour aux événements
        </button>
      </div>
    );
  }

  const totalRevenue = ticketTypes.reduce((acc, tt) => acc + tt.quantity_sold * tt.price_minor, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/events')}
          className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 shadow-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{event.title}</h1>
            <StatusBadge status={event.status} type="event" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">Slug : {event.slug} • ID : {event.id}</p>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto text-xs font-semibold">
        {[
          { key: 'info', label: 'Informations Générales', icon: Calendar },
          { key: 'tickets', label: `Billets (${ticketTypes.length})`, icon: Ticket },
          { key: 'participants', label: 'Participants', icon: Users },
          { key: 'orders', label: 'Commandes', icon: ShoppingCart },
          { key: 'admissions', label: 'Admissions & Scans', icon: QrCode },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                isActive
                  ? 'bg-violet-600 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab: Informations Générales */}
      {activeTab === 'info' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
              <h3 className="text-base font-bold text-slate-900">À propos de l’événement</h3>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                {event.description || event.summary}
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100 text-xs">
                <div>
                  <span className="text-slate-400 block mb-1">Lieu & Salle</span>
                  <span className="font-bold text-slate-800">{event.venue_name}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Adresse complète</span>
                  <span className="font-medium text-slate-700">{event.address}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Date de début</span>
                  <span className="font-medium text-slate-700">{formatDateTime(event.starts_at)}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Date de clôture</span>
                  <span className="font-medium text-slate-700">{formatDateTime(event.ends_at)}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl overflow-hidden border border-slate-100 shadow-sm bg-slate-900 h-48">
              <img src={event.cover_image} alt={event.title} className="w-full h-full object-cover" />
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Devise officielle</span>
                <span className="font-bold text-slate-900">{event.currency}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Fuseau horaire</span>
                <span className="font-bold text-slate-900">{event.timezone}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Catégorie</span>
                <span className="font-bold text-violet-600">{event.category}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Billets */}
      {activeTab === 'tickets' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {ticketTypes.map((tt) => (
            <div key={tt.id} className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm">
              <div className="flex justify-between items-start mb-2">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-violet-50 text-violet-600">
                  {tt.product_kind}
                </span>
                <span className="font-extrabold text-slate-900">
                  {formatMoney(tt.price_minor, 'XOF')}
                </span>
              </div>
              <h4 className="font-bold text-slate-800 text-sm">{tt.name}</h4>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{tt.description}</p>
              <div className="mt-4 pt-3 border-t border-slate-100 flex justify-between text-xs text-slate-600">
                <span>Vendus : <strong>{tt.quantity_sold}</strong></span>
                <span>Total : <strong>{tt.quantity_total}</strong></span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Participants */}
      {activeTab === 'participants' && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <div className="space-y-3">
            {participants.map((p) => (
              <div key={p.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 border border-slate-100 text-xs">
                <div>
                  <span className="font-bold text-slate-900 block">{p.name}</span>
                  <span className="text-slate-400">{p.email} • {p.school}</span>
                </div>
                <span className="font-mono font-bold text-violet-600">{p.serial}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Commandes */}
      {activeTab === 'orders' && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <div className="space-y-3">
            {orders.map((o) => (
              <div key={o.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 border border-slate-100 text-xs">
                <div>
                  <span className="font-bold text-slate-900 block">{o.buyer_name}</span>
                  <span className="text-slate-400 font-mono">{o.id} • {formatDateTime(o.created_at)}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-slate-900">{formatMoney(o.total_minor, o.currency)}</span>
                  <StatusBadge status={o.status} type="order" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Admissions */}
      {activeTab === 'admissions' && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <div className="space-y-3">
            {admissions.map((a) => (
              <div key={a.id} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 border border-slate-100 text-xs">
                <div>
                  <span className="font-bold text-slate-900 block">{a.holder_name} ({a.gate_id})</span>
                  <span className="text-slate-400 font-mono">{a.serial} • {formatDateTime(a.scanned_at)}</span>
                </div>
                <StatusBadge status={a.result} type="admission" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
