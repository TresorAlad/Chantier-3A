import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getGoogleLoginUrl } from '../context/AuthContext';
import { AdminTdevLogo } from '../components/brand/AdminTdevLogo';
import { adminTheme } from '../lib/admin-theme';
import { cn } from '../lib/utils';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { success } = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchParams] = useSearchParams();
  const { error: toastError } = useToast();

  useEffect(() => {
    if (searchParams.get('error') === 'oauth_failed') {
      toastError('Google', 'Connexion Google impossible.');
    }
  }, [searchParams, toastError]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    const ok = await login(email, password);
    setLoading(false);
    if (ok) {
      success('Connexion réussie', 'Bienvenue dans l’administration TDEV.');
      navigate('dashboard');
    }
  };

  return (
    <main className={cn('admin-app min-h-screen p-5 text-zinc-900 lg:grid lg:grid-cols-2 lg:p-8', adminTheme.canvas)}>
      <section className="relative hidden overflow-hidden rounded-[2rem] bg-[#101512] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-20 h-80 w-80 rounded-full bg-emerald-600/20 blur-3xl" />
        <AdminTdevLogo variant="onDark" size="xl" />
        <div className="relative max-w-lg">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.22em] text-zinc-500">
            TDEV Festival 2026
          </p>
          <h1 className="text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
            Une gestion simple pour un grand événement.
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-zinc-400">
            Suivez les inscriptions gratuites, les accès Nexus Night et les scans en direct.
          </p>
        </div>
        <p className="relative text-sm text-zinc-500">Administration sécurisée · Festival 2026</p>
      </section>
      <section className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-md items-center lg:min-h-0">
        <div className="w-full rounded-3xl border border-zinc-200/90 bg-white p-7 shadow-[0_8px_30px_rgba(15,23,42,0.06)] sm:p-10">
          <div className="mb-9">
            <div className="mb-6 flex justify-center">
              <AdminTdevLogo variant="onLight" size="lg" />
            </div>
            <h2 className="text-2xl font-semibold tracking-tight text-zinc-900">Connexion</h2>
            <p className="mt-2 text-sm text-zinc-500">Accédez au tableau de bord organisateur.</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block text-sm font-medium text-zinc-800">
              Adresse e-mail
              <div className="relative mt-2">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-zinc-200 py-2.5 pl-10 pr-3 text-zinc-900 outline-none transition-colors focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/15"
                  placeholder="admin@tdev.bj"
                />
              </div>
            </label>
            <label className="block text-sm font-medium text-zinc-800">
              Mot de passe
              <div className="relative mt-2">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-zinc-400" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-zinc-200 py-2.5 pl-10 pr-3 text-zinc-900 outline-none transition-colors focus:border-emerald-600 focus:ring-2 focus:ring-emerald-600/15"
                  placeholder="Votre mot de passe"
                />
              </div>
            </label>
            <button
              type="submit"
              disabled={loading}
              className={cn('w-full py-3', adminTheme.btnPrimary)}
            >
              {loading ? 'Connexion…' : 'Se connecter'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>
          <a
            href={getGoogleLoginUrl()}
            className={cn('mt-4 w-full py-3', adminTheme.btnSecondary, 'justify-center')}
          >
            Continuer avec Google
          </a>
          <p className="mt-8 flex items-center justify-center gap-2 text-xs text-zinc-500">
            <ShieldCheck className="h-4 w-4 text-emerald-700" />
            Accès réservé à l’organisation.
          </p>
        </div>
      </section>
    </main>
  );
};
