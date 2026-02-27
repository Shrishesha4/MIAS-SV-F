import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  userId: string | null;
  role: string | null;
  isAuthenticated: boolean;
}

function getInitialState(): AuthState {
  if (!browser) {
    return {
      accessToken: null,
      refreshToken: null,
      userId: null,
      role: null,
      isAuthenticated: false,
    };
  }
  return {
    accessToken: localStorage.getItem('accessToken'),
    refreshToken: localStorage.getItem('refreshToken'),
    userId: localStorage.getItem('userId'),
    role: localStorage.getItem('role'),
    isAuthenticated: !!localStorage.getItem('accessToken'),
  };
}

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>(getInitialState());

  return {
    subscribe,
    setTokens: (accessToken: string, refreshToken: string, userId?: string, role?: string) => {
      if (browser) {
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('refreshToken', refreshToken);
        if (userId) localStorage.setItem('userId', userId);
        if (role) localStorage.setItem('role', role);
      }

      update((state) => ({
        ...state,
        accessToken,
        refreshToken,
        userId: userId || state.userId,
        role: role || state.role,
        isAuthenticated: true,
      }));
    },
    logout: () => {
      if (browser) {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('userId');
        localStorage.removeItem('role');
      }

      set({
        accessToken: null,
        refreshToken: null,
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
