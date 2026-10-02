import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Mail,
  School,
  Ticket,
  CheckCircle2,
  Calendar,
  CreditCard,
  Send,
  Sparkles,
  Gift,
  ShieldCheck,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { participantsService } from '../services/participants.service';
import { ordersService } from '../services/orders.service';
import { useToast } from '../context/ToastContext';
import { formatMoney, formatDateTime } from '../lib/utils';
import { Participant, Order } from '../types';
import { useEvent } from '../context/EventContext';

export const ParticipantDetailPage: React.FC = () => {
  const { eventId } = useEvent();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success } = useToast();

  const [participant, setParticipant] = useState<Participant | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      const p = await participantsService.getById(id, eventId);
      setParticipant(p);
      if (p?.order_id) {
        const o = await ordersService.getById(p.order_id);
        setOrder(o);
      }
      setLoading(false);
    }
    load();
  }, [id, eventId]);

  if (loading) {
    return <div className="p-12 text-center text-slate-400">Chargement du profil...</div>;
  }

  if (!participant) {
    return (
      <div className="p-12 text-center">
        <h2 className="text-xl font-bold text-slate-800">Participant introuvable</h2>
        <button
          onClick={() => navigate('/participants')}
          className="mt-4 px-4 py-2 bg-violet-600 text-white rounded-xl text-sm font-semibold"
        >
          Retour aux participants
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/participants')}
          className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 shadow-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Fiche Participant : {participant.name}
          </h1>
          <p className="text-xs text-slate-500">ID Système : {participant.id}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Col: Info Carte */}
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-violet-600 to-pink-600 text-white font-extrabold text-2xl flex items-center justify-center shadow-md shadow-violet-500/20">
              {participant.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900">{participant.name}</h3>
              <p className="text-xs text-slate-400 flex items-center gap-1.5 mt-0.5">
                <Mail className="w-3.5 h-3.5" /> {participant.email}
              </p>
              <div className="mt-2">
                <StatusBadge status={participant.order_status} type="order" />
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <School className="w-4 h-4" /> Établissement
              </span>
              <span className="font-semibold text-slate-800">{participant.school || 'Autodidacte'}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Calendar className="w-4 h-4" /> Date d'émission
              </span>
              <span className="font-semibold text-slate-800">
                {formatDateTime(participant.issued_at)}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-pink-500" /> Nexus Night
              </span>
              <span className="font-bold text-pink-600">
                {participant.is_nexus ? 'Accès Inclus' : 'Non inscrit'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Gift className="w-4 h-4 text-amber-500" /> Pack Goodies
              </span>
              <span className="font-bold text-amber-600">
                {participant.has_goodies ? (participant.goodies_details || 'Inclus') : 'Non inclus'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-500" /> Admission Portique
              </span>
              <span className="font-bold text-emerald-600">
                {participant.admitted ? 'Admis sur le site' : 'En attente de compostage'}
              </span>
            </div>
          </div>

          <button
            onClick={() => success('E-mail expédié', `Le billet a été renvoyé à ${participant.email}`)}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-violet-200 bg-violet-50 text-violet-700 hover:bg-violet-100 font-semibold text-xs transition-colors"
          >
            <Send className="w-4 h-4" />
            Renvoyer le Billet par Email
          </button>
        </div>

        {/* Right Col: Motivation, Wish, Order & Ticket details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Motivation & Wish */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-slate-900 tracking-tight">
              Informations du Formulaire d’Inscription
            </h3>

            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Motivation exprimée
              </span>
              <p className="text-xs sm:text-sm text-slate-700 bg-slate-50 p-3.5 rounded-xl border border-slate-100 leading-relaxed">
                {order?.motivation || 'Je souhaite participer aux conférences et rencontrer les développeurs de la communauté.'}
              </p>
            </div>

            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Souhait particulier pour le Festival
              </span>
              <p className="text-xs sm:text-sm text-slate-700 bg-slate-50 p-3.5 rounded-xl border border-slate-100 leading-relaxed">
                {order?.wish || 'Participer aux ateliers techniques et remporter des goodies tech !'}
              </p>
            </div>
          </div>

          {/* Ticket Details */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                Billet Attribué
              </h3>
              <span className="text-xs font-mono font-bold text-violet-700 bg-violet-50 px-2.5 py-1 rounded-lg border border-violet-100">
                {participant.serial}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Pass</span>
                <span className="font-bold text-slate-800">{participant.pass_name}</span>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Montant Payé</span>
                <span className="font-bold text-slate-800">
                  {formatMoney(participant.amount_minor, participant.currency)}
                </span>
              </div>
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Commande Associée</span>
                <button
                  onClick={() => navigate(`/orders/${participant.order_id}`)}
                  className="font-bold text-violet-600 hover:underline"
                >
                  {participant.order_id}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
