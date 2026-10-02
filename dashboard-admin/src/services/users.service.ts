import { apiFetch } from './api';
import { User, OrganizationMember } from '../types';

export const usersService = {
  async getAll(): Promise<User[]> {
    try {
      return await apiFetch<User[]>('/users');
    } catch {
      return [];
    }
  },

  async getOrgMembers(): Promise<OrganizationMember[]> {
    try {
      return await apiFetch<OrganizationMember[]>('/users');
    } catch {
      return [];
    }
  },

  getCurrentUser(): User | null {
    // Dans une vraie application, cela viendrait d'un contexte d'authentification
    // Pour l'instant on retourne un placeholder qui indique qu'on est connecté
    return {
      id: 'me',
      email: 'admin@tdev.app',
      name: 'Admin TDEV',
      created_at: new Date().toISOString(),
      role: 'admin'
    };
  },
};
