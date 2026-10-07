import { useEffect, type ReactNode } from 'react';

export const STOREFRONT_THEME_CLASS = 'inscription-theme';

/** Thème billetterie unique : rose très clair + blanc (vitrine et pages /inscription). */
export function StorefrontTheme({ children }: { children: ReactNode }) {
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('dark');
    root.classList.add('light', STOREFRONT_THEME_CLASS);
    return () => {
      root.classList.remove(STOREFRONT_THEME_CLASS);
    };
  }, []);

  return <>{children}</>;
}
