import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  iconBgColor?: string;
  trend?: number;
  trendLabel?: string;
  subtitle?: React.ReactNode;
  comparison?: string;
  className?: string;
  loading?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  iconBgColor = 'bg-green-800',
  trend,
  trendLabel = 'vs mois dernier',
  subtitle,
  comparison,
  className,
  loading = false,
}) => {
  if (loading) {
    return (
      <div className={cn("bg-white p-6 rounded-2xl border border-slate-100 shadow-sm animate-pulse", className)}>
        <div className="flex items-center justify-between">
          <div className="w-12 h-12 rounded-xl bg-slate-200"></div>
          <div className="w-16 h-6 rounded-full bg-slate-200"></div>
        </div>
        <div className="mt-4 space-y-2">
          <div className="w-24 h-4 rounded bg-slate-200"></div>
          <div className="w-32 h-8 rounded bg-slate-200"></div>
        </div>
      </div>
    );
  }

  const isPositive = trend !== undefined ? trend >= 0 : true;

  return (
    <div
      className={cn(
        "bg-white p-6 rounded-2xl border border-slate-100 shadow-sm hover:shadow-card-hover transition-all duration-300 group relative overflow-hidden",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-sm shrink-0", iconBgColor)}>
          {icon}
        </div>
        {trend !== undefined && (
          <div
            className={cn(
              "flex items-center gap-0.5 px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide",
              isPositive
                ? "bg-green-50 text-green-700 border border-green-100"
                : "bg-green-100 text-green-900 border border-green-200"
            )}
          >
            {isPositive ? (
              <ArrowUpRight className="w-3.5 h-3.5" />
            ) : (
              <ArrowDownRight className="w-3.5 h-3.5" />
            )}
            <span>{isPositive ? `+${trend}%` : `${trend}%`}</span>
          </div>
        )}
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</p>
        <h3 className="text-2xl font-extrabold text-slate-900 mt-1 tracking-tight">{value}</h3>
      </div>

      {(subtitle || comparison) && (
        <div className="mt-4 pt-3 border-t border-slate-50 flex items-center justify-between text-xs text-slate-500">
          {subtitle && <div>{subtitle}</div>}
          {comparison && (
            <span className="text-slate-400 font-medium ml-auto">
              {comparison} <span className="text-slate-500">{trendLabel}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
