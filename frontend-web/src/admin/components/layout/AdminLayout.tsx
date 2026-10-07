import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { adminTheme } from '../../lib/admin-theme';
import {
  Sidebar,
  readSidebarCollapsed,
  persistSidebarCollapsed,
} from './Sidebar';
import { Header } from './Header';
import { GlobalSearchModal } from './GlobalSearchModal';

export const AdminLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed);

  const handleCollapsedChange = (collapsed: boolean) => {
    setSidebarCollapsed(collapsed);
    persistSidebarCollapsed(collapsed);
  };

  return (
    <div className={cn('admin-app min-h-screen flex text-zinc-800', adminTheme.canvas)}>
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        collapsed={sidebarCollapsed}
        onCollapsedChange={handleCollapsedChange}
      />

      <div
        className={cn(
          'flex min-w-0 flex-1 flex-col transition-[padding-left] duration-300 ease-out',
          sidebarCollapsed ? 'lg:pl-[88px]' : 'lg:pl-[260px]',
        )}
      >
        <Header
          onOpenSidebar={() => setSidebarOpen(true)}
          onOpenSearch={() => setSearchOpen(true)}
        />
        <main className="mx-auto w-full max-w-[1400px] flex-1 p-4 pt-5 sm:p-6 sm:pt-6">
          <Outlet />
        </main>
      </div>

      <GlobalSearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  );
};
