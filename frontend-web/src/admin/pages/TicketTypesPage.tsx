import React, { useState, useEffect } from 'react';
import { Plus, Pencil, Trash2, Ban } from 'lucide-react';
import { PageHeader } from '../components/ui/PageHeader';
import { EmptyState, ErrorState, TableSkeleton } from '../components/ui/FeedbackStates';
import { ticketTypesService } from '../services/ticket-types.service';
import { formatMoney } from '../lib/utils';
import { formatCatalogTicketTypes, type TicketTypeDisplay } from '../lib/ticket-type-catalog-display';
import { useEvent } from '../context/EventContext';
import { useToast } from '../context/ToastContext';
import { adminTheme } from '../lib/admin-theme';
import { cn } from '../lib/utils';
import { adminMessages, adminUserMessage } from '../lib/admin-user-message';
import type { TicketType, PassTier } from '../types';

type Draft = {
  name: string;
  description: string;
  price_minor: number;
  quantity_total: number;
  max_per_order: number;
  pass_tier: PassTier | '';
  status: string;
  product_kind: 'ticket' | 'goodie';
};

const emptyDraft = (): Draft => ({
  name: '',
  description: '',
  price_minor: 0,
  quantity_total: 0,
  max_per_order: 10,
  pass_tier: 'student',
  status: 'active',
  product_kind: 'ticket',
});

function CatalogCard({
  row,
  onEdit,
  onCloseSales,
  onDelete,
}: {
  row: TicketTypeDisplay;
  onEdit: () => void;
  onCloseSales: () => void;
  onDelete: () => void;
}) {
  const { ticket, displayTitle, displayDescription, categoryLabel, gauge } = row;
  const soldOut = !gauge.unlimitedQuota && gauge.remainingLabel === '0';

  return (
    <article className={cn(adminTheme.cardInteractive, 'flex flex-col justify-between p-5')}>
      <div>
        <div className="mb-3 flex items-start justify-between gap-3">
          <span className="rounded-full bg-zinc-100 px-2.5 py-1 text-[11px] font-medium text-zinc-600">
            {categoryLabel}
          </span>
          <span className="text-lg font-semibold tabular-nums text-zinc-900">
            {ticket.price_minor === 0 ? 'Gratuit' : formatMoney(ticket.price_minor, 'XOF')}
          </span>
        </div>
        <h3 className="text-base font-semibold tracking-tight text-zinc-900">{displayTitle}</h3>
        <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-zinc-500">{displayDescription}</p>
        <p className="mt-2 text-[11px] font-medium text-zinc-500">
          Statut :{' '}
          <span className={ticket.status === 'active' ? 'text-emerald-700' : 'text-amber-700'}>
            {ticket.status === 'active' ? 'Ventes ouvertes' : 'Ventes fermées'}
          </span>
          {soldOut && ticket.status === 'active' ? ' · Quota atteint' : null}
        </p>
      </div>

      <div className="mt-6 space-y-3 border-t border-zinc-100 pt-4">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-zinc-500">Ventes</span>
          <span className="font-semibold tabular-nums text-zinc-900">{gauge.soldLabel}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-zinc-100">
          <div
            className="h-full rounded-full bg-emerald-600 transition-all duration-500"
            style={{ width: `${gauge.barWidth}%` }}
          />
        </div>
        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            onClick={onEdit}
            className="inline-flex items-center gap-1 rounded-lg border border-zinc-200 px-2.5 py-1.5 text-xs font-semibold text-zinc-700 hover:bg-zinc-50"
          >
            <Pencil className="h-3.5 w-3.5" />
            Modifier
          </button>
          {ticket.status === 'active' && (
            <button
              type="button"
              onClick={onCloseSales}
              className="inline-flex items-center gap-1 rounded-lg border border-amber-200 px-2.5 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-50"
            >
              <Ban className="h-3.5 w-3.5" />
              Fermer les ventes
            </button>
          )}
          {ticket.quantity_sold === 0 && (
            <button
              type="button"
              onClick={onDelete}
              className="inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2.5 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Supprimer
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

export const TicketTypesPage: React.FC = () => {
  const { eventId } = useEvent();
  const { success, error: toastError } = useToast();
  const [rows, setRows] = useState<TicketTypeDisplay[]>([]);
  const [rawTypes, setRawTypes] = useState<TicketType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [saving, setSaving] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await ticketTypesService.getAll(eventId);
      setRawTypes(data);
      setRows(formatCatalogTicketTypes(data));
    } catch (err: unknown) {
      setError(adminUserMessage(err, adminMessages.genericRetry));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [eventId]);

  const openCreate = () => {
    setEditingId(null);
    setDraft(emptyDraft());
    setEditorOpen(true);
  };

  const openEdit = (tt: TicketType) => {
    setEditingId(tt.id);
    setDraft({
      name: tt.name,
      description: tt.description,
      price_minor: tt.price_minor,
      quantity_total: tt.quantity_total,
      max_per_order: tt.max_per_order,
      pass_tier: (tt.pass_tier as PassTier) || '',
      status: tt.status,
      product_kind: tt.product_kind === 'goodie' ? 'goodie' : 'ticket',
    });
    setEditorOpen(true);
  };

  const saveDraft = async () => {
    if (!eventId || !draft.name.trim()) return;
    setSaving(true);
    try {
      const body = {
        name: draft.name.trim(),
        description: draft.description.trim(),
        price_minor: draft.pass_tier === 'student' ? 0 : draft.price_minor,
        quantity_total: draft.quantity_total,
        max_per_order: draft.max_per_order,
        pass_tier: draft.pass_tier || undefined,
        status: draft.status,
        product_kind: draft.product_kind,
      };
      if (editingId) {
        await ticketTypesService.update(editingId, body);
        success('Pass enregistré', '');
      } else {
        await ticketTypesService.create(eventId, body);
        success('Pass créé', '');
      }
      setEditorOpen(false);
      loadData();
    } catch (err: unknown) {
      toastError('Enregistrement', adminUserMessage(err, adminMessages.passSaveFailed));
    } finally {
      setSaving(false);
    }
  };

  const closeSales = async (tt: TicketType) => {
    try {
      await ticketTypesService.update(tt.id, { status: 'inactive' });
      success('Ventes fermées', '');
      loadData();
    } catch (err: unknown) {
      toastError('Pass', adminUserMessage(err, adminMessages.passSaveFailed));
    }
  };

  const removePass = async (tt: TicketType) => {
    try {
      await ticketTypesService.remove(tt.id);
      success('Pass supprimé', '');
      loadData();
    } catch (err: unknown) {
      toastError('Suppression', adminUserMessage(err, adminMessages.passDeleteBlocked));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Paramètres des passes"
        subtitle="Prix, quotas et activation des offres (Pass Festival, Nexus Night, etc.)"
      >
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-xl bg-emerald-800 px-4 py-2 text-sm font-semibold text-white"
        >
          <Plus className="h-4 w-4" />
          Ajouter un pass
        </button>
      </PageHeader>

      {loading ? (
        <TableSkeleton rows={4} />
      ) : error ? (
        <ErrorState message={error} onRetry={loadData} />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Aucun pass configuré"
          description="Créez une offre pour ouvrir les inscriptions et les paiements."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <CatalogCard
              key={row.ticket.id}
              row={row}
              onEdit={() => {
                const tt = rawTypes.find((t) => t.id === row.ticket.id);
                if (tt) openEdit(tt);
              }}
              onCloseSales={() => {
                const tt = rawTypes.find((t) => t.id === row.ticket.id);
                if (tt) void closeSales(tt);
              }}
              onDelete={() => {
                const tt = rawTypes.find((t) => t.id === row.ticket.id);
                if (tt) void removePass(tt);
              }}
            />
          ))}
        </div>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-6 shadow-xl">
            <h2 className="text-lg font-semibold text-zinc-900">
              {editingId ? 'Modifier le pass' : 'Nouveau pass'}
            </h2>
            <div className="mt-4 space-y-3 text-sm">
              <label className="block font-semibold">
                Nom
                <input
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                />
              </label>
              <label className="block font-semibold">
                Description
                <textarea
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  rows={3}
                  value={draft.description}
                  onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                />
              </label>
              <label className="block font-semibold">
                Palier
                <select
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  value={draft.pass_tier}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      pass_tier: e.target.value as PassTier,
                      price_minor: e.target.value === 'student' ? 0 : draft.price_minor,
                    })
                  }
                >
                  <option value="student">Pass Festival (gratuit)</option>
                  <option value="vip">Nexus / VIP (payant)</option>
                  <option value="standard">Standard</option>
                </select>
              </label>
              {draft.pass_tier !== 'student' && (
                <label className="block font-semibold">
                  Prix (FCFA, centimes)
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                    value={draft.price_minor}
                    onChange={(e) =>
                      setDraft({ ...draft, price_minor: Number(e.target.value) || 0 })
                    }
                  />
                </label>
              )}
              <label className="block font-semibold">
                Quota total (0 = illimité)
                <input
                  type="number"
                  min={0}
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  value={draft.quantity_total}
                  onChange={(e) =>
                    setDraft({ ...draft, quantity_total: Number(e.target.value) || 0 })
                  }
                />
              </label>
              <label className="block font-semibold">
                Max. par commande
                <input
                  type="number"
                  min={1}
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  value={draft.max_per_order}
                  onChange={(e) =>
                    setDraft({ ...draft, max_per_order: Number(e.target.value) || 1 })
                  }
                />
              </label>
              <label className="block font-semibold">
                Statut
                <select
                  className="mt-1 w-full rounded-xl border border-zinc-200 px-3 py-2"
                  value={draft.status}
                  onChange={(e) => setDraft({ ...draft, status: e.target.value })}
                >
                  <option value="active">Ventes ouvertes</option>
                  <option value="inactive">Ventes fermées</option>
                  <option value="hidden">Masqué (vitrine)</option>
                </select>
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-xl border border-zinc-200 px-4 py-2 text-sm font-semibold"
                onClick={() => setEditorOpen(false)}
              >
                Annuler
              </button>
              <button
                type="button"
                disabled={saving}
                className="rounded-xl bg-emerald-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                onClick={() => void saveDraft()}
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
