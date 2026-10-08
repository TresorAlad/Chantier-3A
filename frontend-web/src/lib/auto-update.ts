// Keeps long-lived tabs (restored or suspended by the browser) on the latest
// deploy. The built index.html references hashed bundles, so when the entry
// script it points to differs from the one this tab loaded, a new version
// has been published and we reload.

const ENTRY_RE = /<script[^>]+type="module"[^>]+src="([^"]+)"/;
const MIN_INTERVAL_MS = 60_000;

function loadedEntry(): string | null {
  const el = document.querySelector<HTMLScriptElement>('script[type="module"][src*="/assets/"]');
  return el ? new URL(el.src).pathname : null;
}

async function publishedEntry(): Promise<string | null> {
  const res = await fetch('/', { cache: 'no-store', headers: { Accept: 'text/html' } });
  if (!res.ok) return null;
  const match = ENTRY_RE.exec(await res.text());
  return match ? new URL(match[1], location.origin).pathname : null;
}

export function startAutoUpdate(): void {
  // Only the production build has hashed assets; in dev there is nothing to compare.
  const current = loadedEntry();
  if (!current) return;

  let last = Date.now();
  const check = async () => {
    if (Date.now() - last < MIN_INTERVAL_MS) return;
    last = Date.now();
    try {
      const latest = await publishedEntry();
      if (latest && latest !== current) location.reload();
    } catch {
      // offline or transient error: try again on the next focus
    }
  };

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void check();
  });
  window.addEventListener('pageshow', (e) => {
    if (e.persisted) location.reload();
  });
  // A lazy chunk of a replaced build no longer exists: load the new build.
  window.addEventListener('vite:preloadError', () => location.reload());
}
