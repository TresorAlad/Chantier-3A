import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface AdmissionsBarChartProps {
  data: Array<{ name: string; count: number; fill: string }>;
}

export const AdmissionsBarChart: React.FC<AdmissionsBarChartProps> = ({ data }) => {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm flex flex-col h-full">
      <div className="mb-4">
        <h3 className="text-base font-bold text-slate-900 tracking-tight">
          Statistiques d’Admissions & Scans
        </h3>
        <p className="text-xs text-slate-400 mt-0.5">
          Résultats enregistrés aux différents portiques d’entrée
        </p>
      </div>

      <div className="flex-1 w-full min-h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F1F5F9" />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#64748B' }}
              dy={10}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: '#94A3B8' }}
            />
            <Tooltip
              formatter={(value: any) => [`${value} scans`, 'Nombre']}
              contentStyle={{
                backgroundColor: '#14532d',
                color: '#FFFFFF',
                borderRadius: '12px',
                border: '1px solid #86efac',
                fontSize: '12px',
              }}
            />
            <Bar dataKey="count" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
