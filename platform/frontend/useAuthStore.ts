import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from './useAppStore';
import type { SignupCredentials, SignupResult } from '../services/localAuthService';
import { localAuthService } from '../services/localAuthService';

// Token expiry check: decode JWT payload to get exp claim
function isTokenExpired(token: string): boolean {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return true; // malformed token is considered expired
    const payload = JSON.parse(atob(parts[1]));
    // If no exp claim, assume not expired (short-lived opaque tokens)
    if (!payload.exp) return false;
    return payload.exp * 1000 < Date.now();
  } catch {
    return true; // decode failure => treat as expired
  }
}

// Token refresh: attempt to re-authenticate using the stored token via verify
async function refreshToken(): Promise<{ user: User | null; token: string | null } | null> {
  const currentToken = localAuthService.getAuthToken();
  if (!currentToken) return null;

  try {
    const result = await localAuthService.verifyToken(currentToken);
    return { user: result.user, token: result.token };
  } catch {
    // Token refresh failed; clear stale data
    localAuthService.logout();
    return null;
  }
}

interface AuthState {
  // State
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<User>;
  signup: (creds: SignupCredentials) => Promise<SignupResult>;
  logout: () => void;
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  initialize: () => void;
  refreshIfExpired: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const user = await localAuthService.login({ email, password });
          const token = localAuthService.getAuthToken();
          set({ user, token, isAuthenticated: true, isLoading: false });
          return user;
        } catch (error: any) {
          set({ isLoading: false });
          throw error;
        }
      },

      signup: async (creds: SignupCredentials) => {
        set({ isLoading: true });
        try {
          const result = await localAuthService.signup(creds);
          // If signup returns a token+user (auto-logged-in), persist it
          if (result.token && result.user) {
            set({ user: result.user, token: result.token, isAuthenticated: true, isLoading: false });
          } else {
            set({ isLoading: false });
          }
          return result;
        } catch (error: any) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: () => {
        localAuthService.logout();
        set({ user: null, token: null, refreshToken: null, isAuthenticated: false });
      },

      setUser: (user: User | null) => {
        set({ user, isAuthenticated: !!user && !!get().token });
      },

      setToken: (token: string | null) => {
        const current = get();
        set({ token, isAuthenticated: !!current.user && !!token });
      },

      initialize: () => {
        const token = localAuthService.getAuthToken();
        const user = localAuthService.getCurrentUser();

        if (user && token) {
          // Check if the token is expired; attempt refresh
          const expired = isTokenExpired(token);
          if (expired) {
            refreshToken().then((refreshed) => {
              if (refreshed && refreshed.user && refreshed.token) {
                set({ user: refreshed.user, token: refreshed.token, isAuthenticated: true });
              } else {
                // Refresh failed -- clear stale auth
                set({ user: null, token: null, refreshToken: null, isAuthenticated: false });
              }
            });
          } else {
            set({ user, token, isAuthenticated: true });
          }
        } else {
          // Stale localStorage data -- clean up
          localAuthService.logout();
          set({ user: null, token: null, refreshToken: null, isAuthenticated: false });
        }
      },

      refreshIfExpired: async () => {
        const current = get();
        if (!current.token) return false;

        if (isTokenExpired(current.token)) {
          const refreshed = await refreshToken();
          if (refreshed && refreshed.user && refreshed.token) {
            set({ user: refreshed.user, token: refreshed.token, isAuthenticated: true });
            return true;
          } else {
            set({ user: null, token: null, refreshToken: null, isAuthenticated: false });
            return false;
          }
        }
        return true; // token not expired, no refresh needed
      },
    }),
    {
      name: 'iacgenie-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
