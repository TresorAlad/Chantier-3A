import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Ticket, Sparkles, QrCode, Tags, X, Download, ShoppingCart, Calendar, UserCog } from 'lucide-react';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';

interface SidebarProps { isOpen: boolean; onClose: () => void }

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { user } = useAuth();
  const items = [
    { name: 'Vue d’ensemble', path: 'dashboard', icon: LayoutDashboard },
    { name: 'Événement', path: 'event', icon: Calendar },
    { name: 'Inscrits', path: 'participants', icon: Users },
    { name: 'Commandes', path: 'orders', icon: ShoppingCart },
    { name: 'Billets', path: 'tickets', icon: Ticket },
    { name: 'Nexus Night', path: 'nexus-night', icon: Sparkles },
    { name: 'Scans & admissions', path: 'admissions', icon: QrCode },
    { name: 'Types de pass', path: 'ticket-types', icon: Tags },
    { name: 'Équipe', path: 'team', icon: UserCog },
  ];
  return <>
    {isOpen && <div onClick={onClose} className="fixed inset-0 z-40 bg-green-950/30 lg:hidden" />}
    <aside className={cn('fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-green-900 bg-green-950 text-white transition-transform lg:translate-x-0', isOpen ? 'translate-x-0' : '-translate-x-full')}>
      <div className="flex h-20 items-center justify-between border-b border-green-800 px-6">
        <div className="flex items-center gap-3"><img src="/image.png" alt="TDEV" className="h-9 w-9 brightness-0 invert" /><div><p className="font-bold">TDEV Festival</p><p className="text-[10px] uppercase tracking-widest text-green-200">Administration</p></div></div>
        <button onClick={onClose} className="rounded-lg p-2 text-green-100 lg:hidden"><X className="h-5 w-5" /></button>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        <p className="mb-3 px-3 text-[10px] font-bold tracking-widest text-green-300">BILLETTERIE</p>
        {items.map(({ name, path, icon: Icon }) => <NavLink key={path} to={path} onClick={() => window.innerWidth < 1024 && onClose()} className={cn('flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium text-green-100 hover:bg-green-800', location.pathname === path && 'bg-white text-green-900 shadow-sm')}><Icon className="h-4 w-4" />{name}</NavLink>)}
      </nav>
      <div className="m-4 rounded-2xl border border-green-700 bg-green-900 p-4"><Download className="mb-2 h-5 w-5 text-green-200" /><p className="text-sm font-semibold">Exports CSV</p><p className="mt-1 text-xs text-green-200">Téléchargez les données réelles depuis chaque liste.</p></div>
      <div className="border-t border-green-800 p-4 text-sm"><p className="font-semibold">{user?.name || 'Administrateur'}</p><p className="truncate text-xs text-green-200">{user?.email}</p></div>
    </aside>
  </>;
};
