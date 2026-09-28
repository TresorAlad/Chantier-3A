import { useEffect, useRef, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/use-auth';
import { Spinner } from '@/components/ui/spinner';
import { getStaffSignInPath } from '@/lib/public-links';

const REDIRECT_STORAGE_KEY = 'auth_redirect_data';

const ProtectedRoute = ({ children }: { children: ReactNode }) => {
    const { user, loading } = useAuth();
    const location = useLocation();
    const navigate = useNavigate();
    const wasLoading = useRef(loading);

    useEffect(() => {
        if (loading) {
            wasLoading.current = true;
            return;
        }
        if (!user) {
            const currentPath = location.pathname + location.search;
            localStorage.setItem(REDIRECT_STORAGE_KEY, currentPath);
            navigate(getStaffSignInPath(), { replace: true });
        }
        wasLoading.current = false;
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [user, loading]);

    if (loading) return <Spinner />;
    return user ? children : null;
};

export default ProtectedRoute;
