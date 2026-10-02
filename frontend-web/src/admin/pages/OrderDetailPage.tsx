import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  ShoppingCart,
  User,
  Mail,
  School,
  Calendar,
  CreditCard,
  Send,
  RefreshCw,
  Tag,
} from 'lucide-react';
import { StatusBadge } from '../components/ui/StatusBadge';
import { ordersService } from '../services/orders.service';
import { useToast } from '../context/ToastContext';
import { formatMoney, formatDateTime } from '../lib/utils';
import { Order } from '../types';

export const OrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { success } = useToast();

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!id) return;
      setLoading(true);
      const o = await ordersService.getById(id);
      setOrder(o);
      setLoading(false);
    }
    load();
  }, [id]);

  if (loading) {
    return <div className="p-12 text-center text-slate-400">Chargement de la commande...</div>;
  }

  if (!order) {
    return (
      <div className="p-12 text-center">
        <h2 className="text-xl font-bold text-slate-800">Commande introuvable</h2>
        <button
          onClick={() => navigate('/orders')}
          className="mt-4 px-4 py-2 bg-violet-600 text-white rounded-xl text-sm font-semibold"
        >
          Retour aux commandes
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/orders')}
          className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 shadow-sm transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Détail Commande : {order.id}
          </h1>
          <p className="text-xs text-slate-500">
            Enregistrée le {formatDateTime(order.created_at)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Buyer information */}
        <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm space-y-5">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <h3 className="text-base font-bold text-slate-900">Acheteur</h3>
            <StatusBadge status={order.status} type="order" />
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Nom complet</span>
              <span className="font-bold text-slate-800 text-sm">{order.buyer_name}</span>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">Adresse e-mail</span>
              <span className="font-medium text-slate-700">{order.buyer_email}</span>
            </div>

            <div>
              <span className="text-slate-400 block mb-0.5">École / Université</span>
              <span className="font-medium text-slate-700">
                {order.registration?.school_name ||
                  order.school_name ||
                  String(order.registration?.form?.school_program ?? '') ||
                  'Non spécifié'}
              </span>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 space-y-2">
            <button
              onClick={() => success('Email renvoyé', `Reçu renvoyé à ${order.buyer_email}`)}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs shadow-sm transition-all"
            >
              <Send className="w-4 h-4 text-slate-400" />
              Renvoyer la confirmation
            </button>
          </div>
        </div>

        {/* Payment & Items breakdown */}
        <div className="lg:col-span-2 space-y-6">
          {/* Financial summary card */}
          <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 mb-4">
              Informations de Paiement
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs mb-6">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Montant Total</span>
                <span className="font-extrabold text-slate-900 text-sm">
                  {formatMoney(order.total_minor, order.currency)}
                </span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Passerelle</span>
                <span className="font-bold text-slate-800 uppercase">{order.provider || '—'}</span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Référence</span>
                <span className="font-mono text-slate-700 font-semibold truncate block">
                  {order.provider_ref || '—'}
                </span>
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                <span className="text-slate-400 block mb-1">Paiement Validé</span>
                <span className="font-medium text-slate-700">
                  {formatDateTime(order.paid_at)}
                </span>
              </div>
            </div>

            {/* Motivation from order */}
            {(order.registration?.motivation || order.motivation) && (
              <div className="mt-4 pt-4 border-t border-slate-100 text-xs">
                <span className="font-bold text-slate-500 uppercase tracking-wider block mb-1">
                  Motivation de l&apos;acheteur
                </span>
                <p className="text-slate-700 italic">
                  « {order.registration?.motivation || order.motivation} »
                </p>
              </div>
            )}
            {(order.registration?.form && Object.keys(order.registration.form).length > 0) && (
              <div className="mt-4 pt-4 border-t border-slate-100 text-xs">
                <button
                  type="button"
                  onClick={() => navigate(`/participants/${order.id}`)}
                  className="text-violet-600 font-semibold hover:underline"
                >
                  Voir le formulaire d&apos;inscription complet
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
