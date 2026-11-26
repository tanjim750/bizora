import { create } from 'zustand';
import { browserApi } from '@/lib/api/browser';
import { isApiError } from '@/lib/api/errors';
import type { Customer } from '@/lib/api/types';
import { announce } from './announce-store';
import { useCartStore } from './cart-store';

export type SessionState = {
  user: Customer | null;
  status: 'unknown' | 'guest' | 'signed-in';
  hydrate: () => Promise<void>;
  signIn: (input: { email: string; password: string }) => Promise<Customer>;
  register: (input: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
    phone?: string;
  }) => Promise<Customer>;
  signOut: () => Promise<void>;
};

export const initialSessionState: Omit<
  SessionState,
  'hydrate' | 'signIn' | 'register' | 'signOut'
> = {
  user: null,
  status: 'unknown',
};

export const useSessionStore = create<SessionState>((set) => ({
  ...initialSessionState,

  hydrate: async () => {
    try {
      const user = await browserApi.auth.me();
      set({ user, status: 'signed-in' });
    } catch (err) {
      if (isApiError(err) && err.status === 401) {
        set({ user: null, status: 'guest' });
      } else {
        if (process.env.NODE_ENV === 'development') {
          console.error('Session hydration failed:', err);
        }
        set({ user: null, status: 'guest' });
      }
    }
  },

  signIn: async (input) => {
    const user = await browserApi.auth.signIn(input);
    set({ user, status: 'signed-in' });
    await useCartStore.getState().hydrate();
    announce('Signed in');
    return user;
  },

  register: async (input) => {
    const user = await browserApi.auth.register(input);
    set({ user, status: 'signed-in' });
    await useCartStore.getState().hydrate();
    announce('Account created');
    return user;
  },

  signOut: async () => {
    await browserApi.auth.signOut();
    set({ user: null, status: 'guest' });
    useCartStore.getState().reset();
    await useCartStore.getState().hydrate();
    announce('Signed out');
  },
}));
