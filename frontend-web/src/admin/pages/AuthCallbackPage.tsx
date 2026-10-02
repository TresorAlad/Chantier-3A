import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

function parseHashTokens(): { token: string; refresh: string } | null {
  const raw = window.location.hash.replace(/^#/, '');
  if (!raw) return null;
  const params = new URLSearchParams(raw);
  const token = params.get('token');
  const refresh = params.get('refresh_token');
  if (!token || !refresh) return null;
  return { token, refresh };
}

export const AuthCallbackPage: React.FC = () => {
  const { completeOAuthSession } = useAuth();
  const navigate = useNavigate();
  const [message, setMessage] = useState('Connexion en cours…');

  useEffect(() => {
    const tokens = parseHashTokens();
    if (!tokens) {
      setMessage('Lien de connexion invalide.');
      return;
    }
    window.history.replaceState(null, '', window.location.pathname);
    completeOAuthSession(tokens.token, tokens.refresh).then((ok) => {
      if (ok) navigate('../dashboard', { replace: true });
      else setMessage('Connexion impossible.');
    });
  }, [completeOAuthSession, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
      <p className="text-sm text-slate-600">{message}</p>
    </div>
  );
};
