const TECHNICAL_PATTERN =
  /(\bHTTP\b|\bJSON\b|\bSQL\b|Traceback|Exception|ECONNREFUSED|fetch failed|NetworkError)/i;

export function logAdminApiDiagnostic(context: string, err: unknown): void {
  console.error(`[billetterie:admin:${context}]`, err);
}

export function toUserFacingApiMessage(err: unknown, fallback: string): string {
  const raw = err instanceof Error ? err.message : String(err ?? '');
  if (!raw || TECHNICAL_PATTERN.test(raw)) {
    return fallback;
  }
  if (/^Erreur HTTP \d+/.test(raw)) {
    return fallback;
  }
  return raw.length > 180 ? fallback : raw;
}
