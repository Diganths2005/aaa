import { create } from 'zustand';
import { AuthStore } from '@/types';
import { authAPI } from '@/lib/api';
import Cookies from 'js-cookie';

const tokenCookieOptions = {
  path: '/',
  sameSite: 'strict' as const,
  secure: process.env.NODE_ENV === 'production',
};

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  hydrate: async () => {
    const token = Cookies.get('token') || null;
    if (!token) {
      set({ token: null, user: null, isAuthenticated: false, isLoading: false });
      return;
    }

    set({ token, isLoading: true, error: null });
    try {
      const response = await authAPI.me();
      set({ token, user: response.data, isAuthenticated: true, isLoading: false, error: null });
    } catch {
      Cookies.remove('token', { path: '/' });
      set({ token: null, user: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.login(email.trim(), password);
      const { access_token, user } = response.data;
      Cookies.set('token', access_token, tokenCookieOptions);
      set({ token: access_token, user, isAuthenticated: true, isLoading: false, error: null });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Login failed', isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  signup: async (email: string, firstName: string, lastName: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.signup(email.trim(), firstName.trim(), lastName.trim(), password);
      const { access_token, user } = response.data;
      Cookies.set('token', access_token, tokenCookieOptions);
      set({ token: access_token, user, isAuthenticated: true, isLoading: false, error: null });
    } catch (error: any) {
      set({ error: error.response?.data?.detail || 'Signup failed', isLoading: false, isAuthenticated: false });
      throw error;
    }
  },

  logout: async () => {
    try {
      if (Cookies.get('token')) await authAPI.logout();
    } catch {
      // Always clear the local session even if the server is unreachable.
    } finally {
      Cookies.remove('token', { path: '/' });
      set({ user: null, token: null, isAuthenticated: false, isLoading: false, error: null });
    }
  },
}));