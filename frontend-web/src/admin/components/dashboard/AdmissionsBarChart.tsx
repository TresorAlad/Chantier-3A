import React from 'react';
import { adminChartColors, adminTheme } from '../../lib/admin-theme';
import { cn } from '../../lib/utils';
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
    <div className={cn(adminTheme.card, 'flex h-full flex-col p-5')}>
      <div className="mb-4">
        <h3 className={adminTheme.cardTitle}>
          Statistiques d’Admissions & Scans
        </h3>
        <p className={adminTheme.cardSubtitle}>
          Résultats enregistrés aux différents portiques d’entrée
        </p>
      </div>

      <div className="flex-1 w-full min-h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={adminChartColors.grid} />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: adminChartColors.axis }}
              dy={10}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: adminChartColors.axis }}
            />
            <Tooltip
              formatter={(value: any) => [`${value} scans`, 'Nombre']}
              contentStyle={{
                backgroundColor: adminChartColors.tooltipBg,
                color: '#fafafa',
                borderRadius: '10px',
                border: `1px solid ${adminChartColors.tooltipBorder}`,
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
