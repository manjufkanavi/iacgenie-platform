import { localAuthService } from './localAuthService';
import { useAuthStore } from '../store/useAuthStore';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Redirect the browser to the Keycloak authorization page.
 * The backend handles PKCE and returns a redirect to Keycloak.
 */
export function loginWithKeycloak(redirectUrl?: string): void {
  const params = new URLSearchParams();
  if (redirectUrl) {
    params.set('redirect_uri', redirectUrl);
  }
  const state = window.location.pathname + window.location.search;
  params.set('state', state);
  window.location.href = `${API_BASE}/api/auth/keycloak/login?${params.toString()}`;
}

/**
 * Handle the OAuth callback after Keycloak redirects back with a token.
 * The backend exchanges the authorization code for a local JWT and redirects
 * to the frontend with `?token=<jwt>&provider=keycloak`.
 *
 * Returns true if a Keycloak token was found and processed successfully.
 */
export async function handleKeycloakCallback(): Promise<boolean> {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  const provider = params.get('provider');

  if (!token || provider !== 'keycloak') {
    return false;
  }

  try {
    const result = await localAuthService.verifyToken(token);
    const { setUser, setToken } = useAuthStore.getState();
    setToken(token);
    setUser(result.user);
    window.history.replaceState(null, '', window.location.pathname);
    return true;
  } catch {
    window.history.replaceState(null, '', window.location.pathname);
    throw new Error('Keycloak authentication failed. Please try again.');
  }
}

/**
 * Initiate Keycloak logout via the backend, then clear local state.
 */
export async function logoutWithKeycloak(): Promise<void> {
  try {
    const token = localAuthService.getAuthToken();
    if (token) {
      await fetch(`${API_BASE}/api/auth/keycloak/logout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
      });
    }
  } catch {
    // Best-effort — still clear local state
  }
  localAuthService.logout();
}
