import React from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn } from '../../lib/utils';
import { adminTheme } from '../../lib/admin-theme';

export interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  subtitle?: React.ReactNode;
  comparison?: string;
  className?: string;
  loading?: boolean;
  variant?: 'default' | 'hero';
  /** @deprecated Utiliser le style par défaut du thème */
  iconBgColor?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  trend,
  trendLabel = 'vs mois dernier',
  subtitle,
  comparison,
  className,
  loading = false,
  variant = 'default',
  iconBgColor,
}) => {
  const isHero = variant === 'hero';

  if (loading) {
    return (
      <div
        className={cn(
          isHero ? 'min-h-[148px] animate-pulse rounded-[1.25rem] bg-emerald-800/20' : adminTheme.card,
          'p-5',
          !isHero && 'animate-pulse',
          className,
        )}
      >
        {!isHero && (
          <>
            <div className="flex justify-between">
              <div className="h-11 w-11 rounded-xl bg-zinc-200/80" />
            </div>
            <div className="mt-4 space-y-2">
              <div className="h-3.5 w-24 rounded bg-zinc-200/80" />
              <div className="h-8 w-28 rounded bg-zinc-200/70" />
            </div>
          </>
        )}
      </div>
    );
  }

  const isPositive = trend !== undefined ? trend >= 0 : true;

  if (isHero) {
    return (
      <div className={cn(adminTheme.heroMetric, 'flex flex-col justify-between min-h-[148px]', className)}>
        <div className="flex items-start justify-between gap-3">
          <div className="rounded-xl bg-white/15 p-2.5 text-white">{icon}</div>
          {trend !== undefined && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-white/15 px-2 py-1 text-xs font-semibold">
              {isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
              {isPositive ? `+${trend}%` : `${trend}%`}
            </span>
          )}
        </div>
        <div className="mt-4">
          <p className="text-xs font-medium uppercase tracking-wider text-emerald-100/90">{title}</p>
          <p className="mt-1 text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
          {comparison && (
            <p className="mt-2 text-xs text-emerald-100/80">
              {comparison} <span className="opacity-80">{trendLabel}</span>
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={cn(adminTheme.cardInteractive, 'p-5', className)}>
      <div className="flex items-start justify-between">
        <div className={cn(adminTheme.statIcon, iconBgColor)}>{icon}</div>
        {trend !== undefined && (
          <div
            className={cn(
              'flex items-center gap-0.5 rounded-full border px-2 py-1 text-xs font-semibold',
              isPositive
                ? 'border-emerald-200/80 bg-emerald-50 text-emerald-800'
                : 'border-rose-200/80 bg-rose-50 text-rose-800',
            )}
          >
            {isPositive ? (
              <ArrowUpRight className="h-3.5 w-3.5" />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5" />
            )}
            <span>{isPositive ? `+${trend}%` : `${trend}%`}</span>
          </div>
        )}
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{title}</p>
        <h3 className="mt-1 text-2xl font-semibold tracking-tight text-zinc-900 tabular-nums">{value}</h3>
      </div>

      {(subtitle || comparison) && (
        <div className="mt-4 flex items-center justify-between border-t border-zinc-100 pt-3 text-xs text-zinc-500">
          {subtitle && <div>{subtitle}</div>}
          {comparison && (
            <span className="ml-auto font-medium text-zinc-400">
              {comparison} <span className="text-zinc-500">{trendLabel}</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};
