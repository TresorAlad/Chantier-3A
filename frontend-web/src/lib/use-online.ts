import { useEffect, useState } from 'react';

/** Tracks browser connectivity via the online/offline events. */
export function useOnline() {
    const [online, setOnline] = useState(() => (typeof navigator !== 'undefined' ? navigator.onLine : true));

    useEffect(() => {
        const setTrue = () => setOnline(true);
        const setFalse = () => setOnline(false);
        window.addEventListener('online', setTrue);
        window.addEventListener('offline', setFalse);
        return () => {
            window.removeEventListener('online', setTrue);
            window.removeEventListener('offline', setFalse);
        };
    }, []);

    return online;
}

export default useOnline;
