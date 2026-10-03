import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowRight, Lock, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getGoogleLoginUrl } from '../context/AuthContext';
import { AdminTdevLogo } from '../components/brand/AdminTdevLogo';

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
    <main className="min-h-screen bg-[#f7fcf8] p-5 text-green-950 lg:grid lg:grid-cols-2 lg:p-8">
      <section className="relative hidden overflow-hidden rounded-[2rem] bg-green-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-20 h-80 w-80 rounded-full bg-green-700/70 blur-3xl" />
        <AdminTdevLogo variant="onDark" size="xl" />
        <div className="relative max-w-lg">
          <p className="mb-5 text-sm font-semibold uppercase tracking-[0.25em] text-green-300">
            TDEV Festival 2026
          </p>
          <h1 className="text-5xl font-black leading-tight">
            Une gestion simple pour un grand événement.
          </h1>
          <p className="mt-6 max-w-md text-base leading-7 text-green-100">
            Suivez les inscriptions gratuites, les accès Nexus Night et les scans en direct.
          </p>
        </div>
        <p className="relative text-sm text-green-200">Administration sécurisée · Festival 2026</p>
      </section>
      <section className="mx-auto flex min-h-[calc(100vh-2.5rem)] w-full max-w-md items-center lg:min-h-0">
        <div className="w-full rounded-3xl border border-green-100 bg-white p-7 shadow-xl shadow-green-950/5 sm:p-10">
          <div className="mb-9">
            <div className="mb-6 flex justify-center">
              <AdminTdevLogo variant="onLight" size="lg" />
            </div>
            <h2 className="text-3xl font-black">Connexion</h2>
            <p className="mt-2 text-sm text-green-700">Accédez au tableau de bord organisateur.</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-5">
            <label className="block text-sm font-semibold">
              Adresse e-mail
              <div className="relative mt-2">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-green-700" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-green-200 py-2.5 pl-10 pr-3 outline-none focus:border-green-700 focus:ring-2 focus:ring-green-100"
                  placeholder="admin@tdev.bj"
                />
              </div>
            </label>
            <label className="block text-sm font-semibold">
              Mot de passe
              <div className="relative mt-2">
                <Lock className="absolute left-3 top-3 h-4 w-4 text-green-700" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-green-200 py-2.5 pl-10 pr-3 outline-none focus:border-green-700 focus:ring-2 focus:ring-green-100"
                  placeholder="Votre mot de passe"
                />
              </div>
            </label>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-800 py-3 font-bold text-white transition hover:bg-green-900 disabled:opacity-60"
            >
              {loading ? 'Connexion…' : 'Se connecter'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
          </form>
          <a
            href={getGoogleLoginUrl()}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-green-200 py-3 text-sm font-semibold text-green-900 hover:bg-green-50"
          >
            Continuer avec Google
          </a>
          <p className="mt-8 flex items-center justify-center gap-2 text-xs text-green-700">
            <ShieldCheck className="h-4 w-4" />
            Accès réservé à l’organisation.
          </p>
        </div>
      </section>
    </main>
  );
};
