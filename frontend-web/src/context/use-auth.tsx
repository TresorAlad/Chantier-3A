import React, { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth as authApi, orgs as orgsApi, setToken, onUnauthorized, type CreateOrgInput } from '@/lib/api';
import type { AuthMeResponse, Org, OrgMembership, User } from '@/lib/api-types';
import { getStaffSignInPath } from '@/lib/public-links';

/** Either shape `applySession` is fed: the full /auth/me envelope (carries
 * `orgs`), or the signup/login response (carries `token` but no `orgs` —
 * that gap is real, existing behaviour: orgs is reset to `[]` until the
 * next `refresh()`). */
interface SessionData {
    user: User;
    orgs?: OrgMembership[];
    token?: string;
}

export interface AuthContextValue {
    loading: boolean;
    user: User | null;
    orgs: OrgMembership[];
    activeOrg: OrgMembership | null;
    signUp: (email: string, password: string, name: string) => Promise<User>;
    signIn: (email: string, password: string) => Promise<User>;
    signOut: () => Promise<void>;
    requestPasswordReset: (email: string) => Promise<void>;
    updatePassword: (token: string, password: string) => Promise<void>;
    switchOrg: (orgId: string) => void;
    createOrg: (input: CreateOrgInput) => Promise<Org | undefined>;
    refresh: () => Promise<AuthMeResponse | null>;
}

// The stub methods below are never exercised in practice — app.tsx always
// wraps the tree in a real AuthProvider — but they are typed loosely (not
// as AuthContextValue) rather than coerced to it, so this default cannot
// silently drift from what `createContext` was actually given: it stays
// exactly the no-op shape the untyped original had.
const authContextDefault = {
    loading: true,
    user: null as User | null,
    orgs: [] as OrgMembership[],
    activeOrg: null as OrgMembership | null,
    signUp: () => Promise.resolve(undefined as unknown as User),
    signIn: () => Promise.resolve(undefined as unknown as User),
    signOut: async () => {},
    requestPasswordReset: async () => {},
    updatePassword: async () => {},
    switchOrg: () => {},
    createOrg: () => Promise.resolve(undefined as Org | undefined),
    refresh: () => Promise.resolve(null as AuthMeResponse | null),
};

export const AuthContext = createContext<AuthContextValue>(authContextDefault);

const PROTECTED_PREFIXES = ['/admin', '/checkout', '/orders', '/order/', '/tickets', '/ticket/', '/payment', '/accept-invite'];

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [orgs, setOrgs] = useState<OrgMembership[]>([]);
    const [activeOrgId, setActiveOrgId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    const applySession = useCallback((data: SessionData | null | undefined) => {
        setUser(data?.user ?? null);
        const nextOrgs = data?.orgs ?? [];
        setOrgs(nextOrgs);
        setActiveOrgId((prev) => (prev && nextOrgs.some((o) => o.id === prev) ? prev : nextOrgs[0]?.id ?? null));
    }, []);

    const refresh = useCallback(async () => {
        try {
            const data = await authApi.me({ skipAuthRedirect: true });
            applySession(data);
            return data;
        } catch {
            setUser(null);
            setOrgs([]);
            setActiveOrgId(null);
            return null;
        }
    }, [applySession]);

    useEffect(() => {
        // refresh() catches its own errors (see below) and never rejects, so
        // this is a deliberate fire-and-forget: the effect itself can't be
        // async, and nothing here needs to block on the result.
        void (async () => {
            setLoading(true);
            await refresh();
            setLoading(false);
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(
        () =>
            onUnauthorized(() => {
                setToken(null);
                setUser(null);
                setOrgs([]);
                setActiveOrgId(null);
                // The SEARCH matters as much as the path. Two of the
                // routes reachable here carry their whole payload in the
                // query string — /accept-invite?token=… is a team invite
                // and /payment/verify?reference=… is a settlement — and
                // useAuthRedirect prefers this state over the path
                // ProtectedRoute persists, so a bare pathname here does
                // not merely lose the token, it OVERRIDES the copy that
                // still had it. An invited scanner then lands on "this
                // link is missing its invite code" and cannot join.
                const path = window.location.pathname + window.location.search;
                if (PROTECTED_PREFIXES.some((p) => path.startsWith(p))) {
                    navigate(getStaffSignInPath(), { state: { returnTo: path } });
                }
            }),
        [navigate],
    );

    const signUp = useCallback(
        async (email: string, password: string, name: string) => {
            const data = await authApi.signup({ email, password, name });
            setToken(data.token);
            applySession(data);
            return data.user;
        },
        [applySession],
    );

    const signIn = useCallback(
        async (email: string, password: string) => {
            const data = await authApi.login({ email, password });
            setToken(data.token);
            applySession(data);
            return data.user;
        },
        [applySession],
    );

    const signOut = useCallback(async () => {
        try {
            await authApi.logout();
        } catch {
            // best-effort — clear local state regardless
        }
        setToken(null);
        setUser(null);
        setOrgs([]);
        setActiveOrgId(null);
    }, []);

    const requestPasswordReset = useCallback(async (email: string) => {
        await authApi.passwordReset(email);
    }, []);

    const updatePassword = useCallback(async (token: string, password: string) => {
        await authApi.passwordUpdate(token, password);
    }, []);

    const switchOrg = useCallback(
        (orgId: string) => {
            if (orgs.some((o) => o.id === orgId)) setActiveOrgId(orgId);
        },
        [orgs],
    );

    // createOrg is the only way an account gets its FIRST org: signup
    // creates a user row and nothing else, so until this runs every
    // organiser surface has no org to hang off.
    //
    // It re-reads /api/auth/me rather than splicing the response into
    // local state, because that endpoint is the single source of truth for
    // which orgs a user belongs to and at what role — a create is exactly
    // the moment those must not drift apart. If that re-read fails
    // (offline, transient), the new org is merged in locally so the user
    // isn't bounced straight back to "you have no organisation" having
    // just successfully made one; the next refresh reconciles it.
    const createOrg = useCallback(
        async (input: CreateOrgInput) => {
            const data = await orgsApi.create(input);
            const org = data?.org;

            const session = await authApi.me({ skipAuthRedirect: true }).catch(() => null);
            if (session) {
                applySession(session);
            } else if (org?.id) {
                setOrgs((prev) => (prev.some((o) => o.id === org.id) ? prev : [...prev, org as OrgMembership]));
            }
            // Set last so it wins over applySession's own choice: the org
            // you just created is the one you want to be looking at.
            if (org?.id) setActiveOrgId(org.id);
            return org;
        },
        [applySession],
    );

    const activeOrg = useMemo(() => orgs.find((o) => o.id === activeOrgId) ?? null, [orgs, activeOrgId]);

    const value = useMemo(
        () => ({
            loading,
            user,
            orgs,
            activeOrg,
            signUp,
            signIn,
            signOut,
            requestPasswordReset,
            updatePassword,
            switchOrg,
            createOrg,
            refresh,
        }),
        [loading, user, orgs, activeOrg, signUp, signIn, signOut, requestPasswordReset, updatePassword, switchOrg, createOrg, refresh],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
    return ctx;
}

export default AuthProvider;
