import React, { useState, useEffect } from 'react';
import {
  Users,
  Ticket,
  Sparkles,
  ScanLine,
  Download,
  RefreshCw,
} from 'lucide-react';
import { StatCard } from '../components/ui/StatCard';
import { SalesAreaChart } from '../components/dashboard/SalesAreaChart';
import { TicketDonutChart } from '../components/dashboard/TicketDonutChart';
import { AdmissionsBarChart } from '../components/dashboard/AdmissionsBarChart';
import { PassesProgressCard } from '../components/dashboard/PassesProgressCard';
import { RecentOrdersTable } from '../components/dashboard/RecentOrdersTable';
import { dashboardService } from '../services/dashboard.service';
import { ticketTypesService } from '../services/ticket-types.service';
import { ordersService } from '../services/orders.service';
import { exportsService } from '../services/exports.service';
import { useAuth } from '../context/AuthContext';
import { useEvent } from '../context/EventContext';
import { useToast } from '../context/ToastContext';
import { formatMoney } from '../lib/utils';
import { DashboardKPIData, TicketType, Order } from '../types';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { eventId } = useEvent();
  const { success, error } = useToast();

  const [kpis, setKpis] = useState<DashboardKPIData | null>(null);
  const [salesData, setSalesData] = useState<any[]>([]);
  const [distribution, setDistribution] = useState<any[]>([]);
  const [admissions, setAdmissions] = useState<any[]>([]);
  const [ticketTypes, setTicketTypes] = useState<TicketType[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const kpiRes = await dashboardService.getKPIs(eventId);
        setKpis(kpiRes);
        const results = await Promise.allSettled([
          dashboardService.getSalesChart(eventId),
          dashboardService.getTicketDistribution(eventId),
          dashboardService.getAdmissionStats(eventId),
          ticketTypesService.getAll(eventId),
          ordersService.getAll({ limit: 10 }, eventId),
        ]);
        if (results[0].status === 'fulfilled') setSalesData(results[0].value);
        if (results[1].status === 'fulfilled') setDistribution(results[1].value);
        if (results[2].status === 'fulfilled') setAdmissions(results[2].value);
        if (results[3].status === 'fulfilled') setTicketTypes(results[3].value.filter(tt => tt.product_kind !== 'goodie'));
        if (results[4].status === 'fulfilled') setOrders(results[4].value.data);
      } catch (err) {
        console.error('Error loading dashboard', err);
        error('Données indisponibles', 'Impossible de charger les statistiques.');
      } finally {
        setLoading(false);
      }
    }
    if (!eventId) return;
    loadDashboard();
  }, [error, eventId]);

  const handleExport = async () => {
    try {
      await exportsService.downloadServerCsv('participants', eventId);
      success('Export terminé', 'Le fichier CSV des inscrits a été téléchargé.');
    } catch { error('Export impossible', 'Les données n’ont pas pu être téléchargées.'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Bonjour, {user?.name ? user.name.split(' ')[0] : 'Admin'}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Suivez en temps réel les inscriptions, pass Nexus Night et scans.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-semibold transition-all shadow-sm"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Exporter Rapport</span>
          </button>

        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <StatCard
          title="Participants"
          value={loading ? '...' : (kpis?.participants_count || 0).toLocaleString('fr-FR')}
          icon={<Users className="w-5 h-5 text-white" />}
          iconBgColor="bg-green-800"
          loading={loading}
        />

        <StatCard
          title="Billets émis"
          value={loading ? '...' : (kpis?.tickets_sold || 0).toLocaleString('fr-FR')}
          icon={<Ticket className="w-5 h-5 text-white" />}
          iconBgColor="bg-green-700"
          loading={loading}
        />

        <StatCard
          title="Nexus Night"
          value={loading ? '...' : (kpis?.nexus_night_count || 0).toLocaleString('fr-FR')}
          icon={<Sparkles className="w-5 h-5 text-white" />}
          iconBgColor="bg-green-600"
          trendLabel="Revenus"
          comparison={kpis ? formatMoney(kpis.nexus_night_revenue_minor, kpis.currency || 'XOF') : '...'}
          loading={loading}
        />
        
        <StatCard
          title="Tickets scannés"
          value={loading ? '...' : (kpis?.scans_total || 0).toLocaleString('fr-FR')}
          icon={<ScanLine className="w-5 h-5 text-white" />}
          iconBgColor="bg-green-800"
          loading={loading}
        />

        <StatCard
          title="En attente"
          value={loading ? '...' : (kpis?.pending_orders_count || 0).toLocaleString('fr-FR')}
          icon={<Users className="w-5 h-5 text-white" />}
          iconBgColor="bg-green-500"
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <SalesAreaChart data={salesData} />
        </div>
        <div>
          <TicketDonutChart data={distribution} total={kpis?.tickets_sold || 0} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RecentOrdersTable orders={orders} />
        </div>
        <div className="space-y-6">
          <AdmissionsBarChart data={admissions} />
          <PassesProgressCard ticketTypes={ticketTypes} />
        </div>
      </div>
    </div>
  );
};
