/** Wordmark TDEV (bundlé par Vite → `/assets/…`, fiable sur Vercel et routes admin). */
import tdevWordmarkUrl from '@/assets/brand/tdev-wordmark.png';

export const TDEV_LOGO_URL = tdevWordmarkUrl;

/** Même fichier ; variante claire via `invert` sur fond sombre. */
export const TDEV_LOGO_DARK_URL = tdevWordmarkUrl;

/** Vignette compacte (sidebar, header mobile). */
export const TDEV_TICKET_LOGO_URL = tdevWordmarkUrl;

/** Fallback servi à la racine (vitrine legacy, favicon visuel). */
export const TDEV_LOGO_PUBLIC_URL = '/image.png';
