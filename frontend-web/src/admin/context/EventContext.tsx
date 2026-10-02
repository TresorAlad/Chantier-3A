import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiFetch } from '../services/api';
import { getFestivalEventSlug } from '@/lib/env';

const FESTIVAL_SLUG = getFestivalEventSlug() || 'tdev-festival-2026';

interface EventContextType {
  eventId: string | null;
  orgId: string | null;
  eventSlug: string;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const EventContext = createContext<EventContextType>({
  eventId: null,
  orgId: null,
  eventSlug: FESTIVAL_SLUG,
  loading: true,
  error: null,
  reload: () => {},
});

export const EventProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [eventId, setEventId] = useState<string | null>(localStorage.getItem('tdev_event_id'));
  const [orgId, setOrgId] = useState<string | null>(localStorage.getItem('tdev_org_id'));
  const [loading, setLoading] = useState(!eventId);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function resolve() {
      setLoading(true);
      setError(null);
      try {
        const res = await apiFetch<{
          event: { id: string; org_id: string; slug?: string };
        }>(`/events/${FESTIVAL_SLUG}`);
        if (cancelled) return;
        setEventId(res.event.id);
        setOrgId(res.event.org_id);
        localStorage.setItem('tdev_event_id', res.event.id);
        localStorage.setItem('tdev_org_id', res.event.org_id);
      } catch {
        if (!cancelled) {
          setError('Impossible de charger l’événement festival.');
          setEventId(null);
          setOrgId(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    resolve();
    return () => {
      cancelled = true;
    };
  }, [tick]);

  return (
    <EventContext.Provider
      value={{
        eventId,
        orgId,
        eventSlug: FESTIVAL_SLUG,
        loading,
        error,
        reload: () => {
          localStorage.removeItem('tdev_event_id');
          localStorage.removeItem('tdev_org_id');
          setEventId(null);
          setOrgId(null);
          setTick((t) => t + 1);
        },
      }}
    >
      {children}
    </EventContext.Provider>
  );
};

export const useEvent = () => useContext(EventContext);

export function requireEventId(eventId: string | null): string {
  if (!eventId) {
    throw new Error('Événement non configuré');
  }
  return eventId;
}
