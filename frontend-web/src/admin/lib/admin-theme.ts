/** Tokens UI partagés pour le dashboard admin (style SaaS clair). */
export const ADMIN_RAIL_WIDTH = 88;
export const ADMIN_SIDEBAR_WIDTH_EXPANDED = 260;

export const adminTheme = {
  canvas: 'bg-[#f4f5f7]',
  card: 'rounded-[1.25rem] border border-zinc-200/70 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.04)]',
  cardInteractive:
    'rounded-[1.25rem] border border-zinc-200/70 bg-white shadow-[0_1px_3px_rgba(15,23,42,0.04)] transition-shadow hover:shadow-[0_8px_24px_rgba(15,23,42,0.07)]',
  cardTitle: 'text-base font-semibold text-zinc-900 tracking-tight',
  cardSubtitle: 'mt-0.5 text-xs text-zinc-500',
  pageTitle: 'text-[1.65rem] font-semibold text-zinc-900 tracking-tight sm:text-[1.85rem]',
  pageSubtitle: 'mt-1 text-sm text-zinc-500',
  btnPrimary:
    'inline-flex items-center justify-center gap-2 rounded-xl bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-zinc-800',
  btnSecondary:
    'inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2.5 text-sm font-semibold text-zinc-700 shadow-sm transition-colors hover:border-zinc-300 hover:bg-zinc-50',
  statIcon:
    'flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-600/10 text-emerald-700',
  linkAccent: 'text-emerald-700 font-semibold hover:text-emerald-900 transition-colors',
  heroMetric:
    'rounded-[1.25rem] bg-gradient-to-br from-emerald-700 via-emerald-800 to-emerald-950 p-5 text-white shadow-[0_12px_32px_rgba(6,95,70,0.35)] border-0',
} as const;

export const adminChartColors = {
  primary: '#059669',
  primarySoft: 'rgba(5, 150, 105, 0.15)',
  grid: '#e8eaed',
  axis: '#9ca3af',
  tooltipBg: '#18181b',
  tooltipBorder: '#3f3f46',
} as const;

export const adminSidebar = {
  shell: 'border-r border-zinc-200/80 bg-[#eef0f2]',
  iconIdle:
    'text-zinc-500 hover:bg-white/80 hover:text-zinc-800 hover:shadow-sm',
  iconActive: 'bg-emerald-700 text-white shadow-md shadow-emerald-900/20',
  mobileShell: 'border-r border-zinc-200 bg-white',
} as const;
