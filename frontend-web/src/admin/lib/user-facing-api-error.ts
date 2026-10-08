const TECHNICAL_PATTERN =
  /(\bHTTP\b|\bJSON\b|\bSQL\b|Traceback|Exception|ECONNREFUSED|fetch failed|NetworkError)/i;

const ENGLISH_API_PATTERN =
  /\b(you are not|you cannot|forbidden|invalid_request|not_found|internal_error|authentication required)\b/i;

export function logAdminApiDiagnostic(context: string, err: unknown): void {
  console.error(`[billetterie:admin:${context}]`, err);
}

export function toUserFacingApiMessage(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : String(err ?? '');
  if (!raw || TECHNICAL_PATTERN.test(raw) || ENGLISH_API_PATTERN.test(raw)) {
    return fallback;
  }
  if (/^Erreur HTTP \d+/.test(raw)) {
    return fallback;
  }
  if (/^[a-z][a-z0-9_ -]{2,120}$/i.test(raw) && /[a-z]{4,}/.test(raw) && !/[àâäéèêëïîôùûüç]/i.test(raw)) {
    return fallback;
  }
  return raw.length > 180 ? fallback : raw;
}
