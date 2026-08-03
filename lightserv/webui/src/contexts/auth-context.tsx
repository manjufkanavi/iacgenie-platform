"use client";

import {
  type ReactNode,
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";

const TOKEN_KEY = "auth_token";
const USER_KEY = "auth_user";

interface AuthUser {
  id: string;
  username: string;
  email?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<Record<string, unknown>>;
  loginWithKeycloak: () => void;
  setCredentials: (token: string, user: AuthUser) => void;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

function getStorageValue(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key);
}

function setStorageValue(key: string, value: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(key, value);
  }
}

function removeStorageValue(key: string): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(key);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = getStorageValue(TOKEN_KEY);
    const savedUser = getStorageValue(USER_KEY);
    if (savedToken) {
      setTokenState(savedToken);
    }
    if (savedUser) {
      try {
        setUserState(JSON.parse(savedUser));
      } catch {
        removeStorageValue(USER_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const setToken = useCallback(
    (newToken: string | null, newUser: AuthUser | null) => {
      setTokenState(newToken);
      setUserState(newUser);
      if (newToken && newUser) {
        setStorageValue(TOKEN_KEY, newToken);
        setStorageValue(USER_KEY, JSON.stringify(newUser));
      } else {
        removeStorageValue(TOKEN_KEY);
        removeStorageValue(USER_KEY);
      }
    },
    []
  );

  const setCredentials = useCallback(
    (newToken: string, newUser: AuthUser) => {
      setTokenState(newToken);
      setUserState(newUser);
      setStorageValue(TOKEN_KEY, newToken);
      setStorageValue(USER_KEY, JSON.stringify(newUser));
    },
    []
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await fetch("/api/auth?path=/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Login failed");
      }
      setToken(data.token, { id: data.userId, username: data.username || email, email });
    },
    [setToken]
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await fetch("/api/auth?path=/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: name, email, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || "Registration failed");
      }
      return data;
    },
    []
  );

  const loginWithKeycloak = useCallback(() => {
    const keycloakUrl =
      (typeof process !== "undefined" &&
        (process.env.NEXT_PUBLIC_KEYCLOAK_URL as string)) ||
      "https://keycloak.iacgenie.com";
    const realm =
      (typeof process !== "undefined" &&
        (process.env.NEXT_PUBLIC_KEYCLOAK_REALM as string)) ||
      "lightserp";
    const clientId =
      (typeof process !== "undefined" &&
        (process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID as string)) ||
      "lightserp-webui";

    const redirectUri =
      (typeof process !== "undefined" &&
        (process.env.NEXT_PUBLIC_REDIRECT_URI as string)) ||
      `${window.location.origin}/auth/callback`;

    const state = Math.random().toString(36).substring(2) + Date.now().toString(36);
    const url = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;
    window.location.href = url;
  }, []);

  const logout = useCallback(() => {
    setToken(null, null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }, [setToken]);

  const refreshToken = useCallback(async () => {
    if (!token) return;
    const res = await fetch("/api/auth?path=/api/auth/refresh", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      logout();
      throw new Error(data.error || "Token refresh failed");
    }
    const data = await res.json();
    setToken(data.token, user);
  }, [token, user, logout, setToken]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token,
        login,
        register,
        loginWithKeycloak,
        setCredentials,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
