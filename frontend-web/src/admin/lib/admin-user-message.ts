import { logAdminApiDiagnostic, toUserFacingApiMessage } from './user-facing-api-error';

export const adminMessages = {
  genericRetry: 'Réessayez dans un instant.',
  actionDenied: 'Action non autorisée.',
  roleChangeDenied: 'Vous ne pouvez pas modifier ce rôle.',
  inviteFailed: 'Invitation impossible.',
  inviteCreatedEmail: (email: string) => `E-mail envoyé à ${email}.`,
  inviteCreatedClipboard:
    'Invitation créée. Lien copié dans le presse-papiers (e-mail non disponible).',
  exportNone: 'Aucune inscription à exporter.',
  exportFailed: 'Export impossible. Réessayez dans un instant.',
  exportSuccess: 'Le fichier a été téléchargé.',
  passDeleteBlocked: 'Ce pass a déjà des ventes. Fermez les ventes plutôt que de le supprimer.',
  passSaveFailed: 'Enregistrement impossible. Réessayez dans un instant.',
  loadTeamFailed: 'Impossible de charger l’équipe.',
} as const;

const ENGLISH_API_SNIPPETS: Record<string, string> = {
  forbidden: adminMessages.actionDenied,
  'you are not': adminMessages.actionDenied,
  'you cannot': adminMessages.roleChangeDenied,
  'invalid role': adminMessages.roleChangeDenied,
  'member not found': adminMessages.genericRetry,
  conflict: adminMessages.passDeleteBlocked,
  'ticket type has sales': adminMessages.passDeleteBlocked,
};

export function adminUserMessage(err: unknown, fallback: string): string {
  logAdminApiDiagnostic('ui', err);
  const raw = err instanceof Error ? err.message : String(err ?? '');
  const lower = raw.toLowerCase();
  for (const [needle, msg] of Object.entries(ENGLISH_API_SNIPPETS)) {
    if (lower.includes(needle)) return msg;
  }
  return toUserFacingApiMessage(err, fallback);
}
