import React from 'react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

interface SalesAreaChartProps { data: Array<{ date: string; orders: number; tickets: number }> }

export const SalesAreaChart: React.FC<SalesAreaChartProps> = ({ data }) => (
  <section className="flex h-full flex-col rounded-2xl border border-green-100 bg-white p-5 shadow-sm">
    <div className="mb-3 flex items-start justify-between gap-3"><div><h3 className="font-bold text-green-950">Évolution des inscriptions</h3><p className="mt-1 text-xs text-green-700">Données réelles des 7 derniers jours</p></div><span className="rounded-full bg-green-50 px-3 py-1 text-xs font-semibold text-green-800">Inscriptions</span></div>
    <div className="min-h-[220px] flex-1"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 6, left: -20, bottom: 0 }}><defs><linearGradient id="registrations" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#18753d" stopOpacity={0.22} /><stop offset="100%" stopColor="#18753d" stopOpacity={0} /></linearGradient></defs><CartesianGrid stroke="#dcfce7" strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#4b7b5a' }} /><YAxis axisLine={false} tickLine={false} allowDecimals={false} tick={{ fontSize: 11, fill: '#4b7b5a' }} /><Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #bbf7d0', color: '#14532d' }} formatter={(value: any) => [value, 'Inscriptions']} /><Area type="monotone" dataKey="tickets" stroke="#18753d" strokeWidth={3} fill="url(#registrations)" dot={{ r: 3, fill: '#ffffff', stroke: '#18753d', strokeWidth: 2 }} /></AreaChart></ResponsiveContainer></div>
  </section>
);
