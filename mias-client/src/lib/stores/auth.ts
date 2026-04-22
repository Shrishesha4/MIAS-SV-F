import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthState {
  accessToken: string | null;
  userId: string | null;
  role: string | null;
  isAuthenticated: boolean;
}

function getInitialState(): AuthState {
  if (!browser) {
    return {
      accessToken: null,
      userId: null,
      role: null,
      isAuthenticated: false,
    };
  }
  // Access token is never persisted to localStorage (memory only).
  // userId and role are kept for UI pre-population only; the server always
  // re-validates identity via the access token.
  return {
    accessToken: null,
    userId: localStorage.getItem('userId'),
    role: localStorage.getItem('role'),
    isAuthenticated: false,
  };
}

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>(getInitialState());

  return {
    subscribe,
    setTokens: (accessToken: string, userId?: string, role?: string) => {
      if (browser) {
        // Access token is memory-only — never written to localStorage.
        // userId and role are safe to persist (not credentials).
        if (userId) localStorage.setItem('userId', userId);
        if (role) localStorage.setItem('role', role);
      }

      update((state) => ({
        ...state,
        accessToken,
        userId: userId || state.userId,
        role: role || state.role,
        isAuthenticated: true,
      }));
    },
    logout: () => {
      if (browser) {
        localStorage.removeItem('userId');
        localStorage.removeItem('role');
      }

      set({
        accessToken: null,
        userId: null,
        role: null,
        isAuthenticated: false,
      });
    },
  };
}

export const authStore = createAuthStore();
export const isAuthenticated = derived(authStore, ($auth) => $auth.isAuthenticated);
export const userRole = derived(authStore, ($auth) => $auth.role);
export const userId = derived(authStore, ($auth) => $auth.userId);
