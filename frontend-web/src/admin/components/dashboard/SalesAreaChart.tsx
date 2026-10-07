import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { adminChartColors, adminTheme } from '../../lib/admin-theme';
import { cn } from '../../lib/utils';

interface SalesAreaChartProps {
  data: Array<{ date: string; orders: number; tickets: number }>;
}

export const SalesAreaChart: React.FC<SalesAreaChartProps> = ({ data }) => (
  <section className={cn(adminTheme.card, 'flex h-full min-h-[320px] flex-col p-5')}>
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h3 className={adminTheme.cardTitle}>Inscriptions (7 jours)</h3>
        <p className={adminTheme.cardSubtitle}>Nombre d’inscriptions par jour</p>
      </div>
      <span className="rounded-full border border-emerald-200/80 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
        Temps réel
      </span>
    </div>
    <div className="min-h-[240px] flex-1">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }} barSize={28}>
          <CartesianGrid stroke={adminChartColors.grid} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 11, fill: adminChartColors.axis }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            allowDecimals={false}
            tick={{ fontSize: 11, fill: adminChartColors.axis }}
          />
          <Tooltip
            cursor={{ fill: adminChartColors.primarySoft }}
            contentStyle={{
              borderRadius: 10,
              border: `1px solid ${adminChartColors.tooltipBorder}`,
              backgroundColor: adminChartColors.tooltipBg,
              color: '#fafafa',
              fontSize: 12,
            }}
            formatter={(value) => [value ?? 0, 'Inscriptions']}
          />
          <Bar dataKey="tickets" fill={adminChartColors.primary} radius={[10, 10, 4, 4]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  </section>
);
