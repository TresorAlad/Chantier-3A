// Client API centralisé TDEV Billetterie.
// Permet de basculer instantanément entre les données mockées et le vrai backend FastAPI.

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api';
// Les données de démonstration ne sont jamais activées par défaut : l’admin doit
// refléter exactement la base Neon, y compris lorsqu’une erreur doit être corrigée.
export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true';

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('tdev_admin_token');
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('tdev_admin_token', token);
    } else {
      localStorage.removeItem('tdev_admin_token');
    }
  }

  getToken(): string | null {
    return this.token;
  }

  async fetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
    const url = `${API_URL}${cleanEndpoint}`;

    const response = await fetch(url, {
      ...options,
      headers,
      credentials: 'omit',
    });

    if (!response.ok) {
      let errorMsg = `Erreur HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        const detail = errorJson.detail || errorJson.error?.message || errorJson.message;
        if (detail) errorMsg = typeof detail === 'string' ? detail : JSON.stringify(detail);
      } catch {
        // pas de corps json
      }
      throw new Error(errorMsg);
    }

    return response.json();
  }

  async download(endpoint: string, filename: string): Promise<void> {
    const response = await fetch(`${API_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`, {
      headers: this.token ? { Authorization: `Bearer ${this.token}` } : undefined,
    });
    if (!response.ok) {
      let message = `Export impossible (${response.status})`;
      try { const body = await response.json(); message = body.detail || body.error?.message || message; } catch { /* no JSON body */ }
      throw new Error(message);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = filename; link.click();
    URL.revokeObjectURL(url);
  }
}

export const apiClient = new ApiClient();
export const apiFetch = <T>(endpoint: string, options?: RequestInit) => 
  apiClient.fetch<T>(`/admin${endpoint}`, options);

export const authFetch = <T>(endpoint: string, options?: RequestInit) => 
  apiClient.fetch<T>(`/auth${endpoint}`, options);
