import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMoney(minor: number = 0, currency: string = 'XOF'): string {
  const major = minor / 100;
  try {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency === 'ZAR' ? 'ZAR' : (currency === 'USD' ? 'USD' : 'XOF'),
      maximumFractionDigits: 0,
    }).format(major);
  } catch {
    return `${major.toLocaleString('fr-FR')} ${currency}`;
  }
}

export function formatDate(value?: string | null): string {
  if (!value) return '—';
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(d);
  } catch {
    return value;
  }
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—';
  try {
    const d = new Date(value);
    if (isNaN(d.getTime())) return value;
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(d);
  } catch {
    return value;
  }
}

export function formatRelativeTime(value?: string | null): string {
  if (!value) return '—';
  try {
    const d = new Date(value);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'À l’instant';
    if (diffMins < 60) return `Il y a ${diffMins} min`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays === 1) return 'Hier';
    return `Il y a ${diffDays}j`;
  } catch {
    return value;
  }
}
