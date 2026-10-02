import React from 'react';
import { TicketType } from '../../types';
import { formatMoney } from '../../lib/utils';
import { Tag, ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface PassesProgressCardProps {
  ticketTypes: TicketType[];
}

export const PassesProgressCard: React.FC<PassesProgressCardProps> = ({ ticketTypes }) => {
  const colors = ['bg-green-900', 'bg-green-800', 'bg-green-700', 'bg-green-600', 'bg-green-500'];

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            Ventes par Types de Produits
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Taux de remplissage des jauges et quotas
          </p>
        </div>
        <Link
          to="/ticket-types"
          className="text-xs font-semibold text-green-700 hover:text-green-900 flex items-center gap-1"
        >
          Détails <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      <div className="flex-1 space-y-4">
        {ticketTypes.slice(0, 5).map((tt, idx) => {
          const percent = Math.min(
            100,
            Math.round((tt.quantity_sold / (tt.quantity_total || 1)) * 100)
          );
          const barColor = colors[idx % colors.length];

          return (
            <div key={tt.id} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600 font-semibold text-[11px]">
                    <Tag className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="font-bold text-slate-800 block">{tt.name}</span>
                    <span className="text-[11px] text-slate-400">
                      {formatMoney(tt.price_minor, 'XOF')}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="font-extrabold text-slate-900">
                    {tt.quantity_sold} / {tt.quantity_total}
                  </span>
                  <span className="text-[11px] text-slate-500 block">{percent}%</span>
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${barColor} transition-all duration-500`}
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
