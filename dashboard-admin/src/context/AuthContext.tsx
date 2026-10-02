import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { apiClient, authFetch } from '../services/api';
import { useToast } from './ToastContext';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password?: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { error } = useToast();

  useEffect(() => {
    async function loadUser() {
      const token = apiClient.getToken();
      if (token) {
        try {
          const res = await authFetch<{ user: User }>('/me');
          setUser(res.user);
        } catch (err) {
          apiClient.setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    }
    loadUser();
  }, []);

  const login = async (email: string, password?: string): Promise<boolean> => {
    setIsLoading(true);
    try {
      const res = await authFetch<{ user: User; token: string }>('/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      apiClient.setToken(res.token);
      setUser(res.user);
      return true;
    } catch (err: any) {
      error('Erreur de connexion', err.message || 'Identifiants invalides');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authFetch('/logout', { method: 'POST' });
    } catch (e) {
      // ignore
    }
    apiClient.setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
