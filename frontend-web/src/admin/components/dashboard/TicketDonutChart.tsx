import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface TicketDonutChartProps {
  data: Array<{ name: string; value: number; color: string }>;
  total: number;
}

export const TicketDonutChart: React.FC<TicketDonutChartProps> = ({ data, total }) => {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="mb-4">
        <h3 className="text-base font-bold text-slate-900 tracking-tight">
          Répartition par Type de Pass
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Ventilation des ventes sur l’ensemble du festival
        </p>
      </div>

      <div className="flex-1 flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Donut with center text */}
        <div className="relative w-48 h-48 sm:w-52 sm:h-52 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Tooltip
                formatter={(value: any, name: any) => [`${value} unités`, name]}
                contentStyle={{
                  backgroundColor: '#0F172A',
                  color: '#FFFFFF',
                  borderRadius: '12px',
                  border: 'none',
                  fontSize: '12px',
                }}
              />
              <Pie
                data={data}
                innerRadius={58}
                outerRadius={80}
                paddingAngle={4}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span className="text-2xl font-extrabold text-slate-900 leading-tight">
              {total.toLocaleString('fr-FR')}
            </span>
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Total Vendu
            </span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 w-full space-y-2.5">
          {data.map((item, idx) => {
            const percent = ((item.value / (total || 1)) * 100).toFixed(1);
            return (
              <div key={idx} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="font-medium text-slate-700 truncate max-w-[120px] sm:max-w-none">
                    {item.name}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-right">
                  <span className="font-bold text-slate-900">{item.value}</span>
                  <span className="text-slate-400 text-[11px] w-12">({percent}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
