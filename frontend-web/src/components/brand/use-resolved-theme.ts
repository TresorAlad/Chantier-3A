import { useEffect, useState } from 'react';
import { useTheme } from '@/components/theme-provider';

/** Thème effectif (light / dark) y compris mode système. */
export function useResolvedTheme(): 'light' | 'dark' {
    const { theme } = useTheme();
    const [resolved, setResolved] = useState<'light' | 'dark'>(() =>
        typeof document !== 'undefined' && document.documentElement.classList.contains('dark') ? 'dark' : 'light',
    );

    useEffect(() => {
        const read = () => {
            if (theme === 'dark') return 'dark' as const;
            if (theme === 'light') return 'light' as const;
            return window.matchMedia('(prefers-color-scheme: dark)').matches ? ('dark' as const) : ('light' as const);
        };
        setResolved(read());
        const root = document.documentElement;
        const observer = new MutationObserver(() => {
            setResolved(root.classList.contains('dark') ? 'dark' : 'light');
        });
        observer.observe(root, { attributes: true, attributeFilter: ['class'] });
        const media = window.matchMedia('(prefers-color-scheme: dark)');
        const onMedia = () => {
            if (theme === 'system') setResolved(media.matches ? 'dark' : 'light');
        };
        media.addEventListener('change', onMedia);
        return () => {
            observer.disconnect();
            media.removeEventListener('change', onMedia);
        };
    }, [theme]);

    return resolved;
}
