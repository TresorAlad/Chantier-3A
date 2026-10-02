import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar,
  MapPin,
  Clock,
  Plus,
  Eye,
  ExternalLink,
} from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { StatusBadge } from '../components/ui/StatusBadge';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { eventsService } from '../services/events.service';
import { formatDate } from '../lib/utils';
import { Event } from '../types';

export const EventsPage: React.FC = () => {
  const navigate = useNavigate();
  const [eventsList, setEventsList] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await eventsService.getAll();
      setEventsList(data);
    } catch (err: any) {
      setError(err.message || 'Impossible de récupérer les événements.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Gestion des Événements & Festivals"
        subtitle="Supervisez les dates, lieux, statuts de publication et fiches festival"
      />

      {loading ? (
        <TableSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {eventsList.map((e) => (
            <div
              key={e.id}
              onClick={() => navigate(`/events/${e.id}`)}
              className="bg-white rounded-2xl border border-slate-100 shadow-sm hover:shadow-card-hover transition-all duration-300 overflow-hidden flex flex-col justify-between cursor-pointer group"
            >
              <div>
                {/* Cover Image */}
                <div className="relative h-44 w-full bg-slate-900 overflow-hidden">
                  <img
                    src={e.cover_image}
                    alt={e.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 opacity-90"
                  />
                  <div className="absolute top-3 right-3">
                    <StatusBadge status={e.status} type="event" />
                  </div>
                  <div className="absolute bottom-3 left-3">
                    <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-900/80 backdrop-blur-md text-white border border-white/10">
                      {e.category}
                    </span>
                  </div>
                </div>

                <div className="p-5">
                  <h3 className="text-base font-bold text-slate-900 group-hover:text-violet-600 transition-colors line-clamp-1">
                    {e.title}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                    {e.summary}
                  </p>

                  <div className="mt-4 space-y-2 text-xs text-slate-600">
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{e.venue_name} ({e.address})</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>
                        Du {formatDate(e.starts_at)} au {formatDate(e.ends_at)}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="px-5 py-3.5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs">
                <span className="font-mono text-slate-400">{e.slug}</span>
                <span className="font-semibold text-violet-600 flex items-center gap-1">
                  Gérer l’événement <Eye className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
