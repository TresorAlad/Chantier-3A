import React from 'react';
import { Menu, Search, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps { onOpenSidebar: () => void; onOpenSearch: () => void }
export const Header: React.FC<HeaderProps> = ({ onOpenSidebar, onOpenSearch }) => {
  const { user, logout } = useAuth(); const navigate = useNavigate();
  return <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-green-100 bg-white/95 px-4 backdrop-blur sm:px-6">
    <div className="flex flex-1 items-center gap-3"><button onClick={onOpenSidebar} className="rounded-lg p-2 text-green-800 hover:bg-green-50 lg:hidden"><Menu className="h-5 w-5" /></button><button onClick={onOpenSearch} className="hidden w-full max-w-sm items-center gap-2 rounded-xl border border-green-100 bg-green-50/50 px-3 py-2 text-left text-sm text-green-700 hover:border-green-300 sm:flex"><Search className="h-4 w-4" />Rechercher un inscrit ou un billet</button></div>
    <div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-sm font-semibold text-green-950">{user?.name || 'Administrateur'}</p><p className="text-xs text-green-700">{user?.email}</p></div><button onClick={() => { logout(); navigate('/login'); }} title="Déconnexion" className="rounded-xl border border-green-200 p-2 text-green-800 hover:bg-green-50"><LogOut className="h-4 w-4" /></button></div>
  </header>;
};
