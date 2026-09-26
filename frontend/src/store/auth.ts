import { create } from 'zustand';
import { AuthStore, User } from '@/types';
import { authAPI } from '@/lib/api';
import Cookies from 'js-cookie';

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  hydrate: () => {
    const token = Cookies.get('token') || null;
    set({ token, isAuthenticated: !!token });
  },

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.login(email, password);
      const { access_token, user } = response.data;
      
      Cookies.set('token', access_token);
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Login failed',
        isLoading: false,
      });
      throw error;
    }
  },

  signup: async (email: string, firstName: string, lastName: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.signup(email, firstName, lastName, password);
      const { access_token, user } = response.data;
      
      Cookies.set('token', access_token);
      set({
        token: access_token,
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        error: error.response?.data?.detail || 'Signup failed',
        isLoading: false,
      });
      throw error;
    }
  },

  logout: () => {
    Cookies.remove('token');
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    });
  },
}));
