/**
 * Authentication Configuration Service
 * Discovers available auth providers from the backend and exposes them for reactive UI rendering.
 */

export interface AuthProviderConfig {
  id: string;
  name: string;
  enabled: boolean;
}

export interface AuthConfig {
  providers: AuthProviderConfig[];
  samlEnabled: boolean;
  googleEnabled: boolean;
  githubEnabled: boolean;
  localEnabled: boolean;
}

const DEFAULT_CONFIG: AuthConfig = {
  providers: [
    { id: 'local', name: 'Local Email/Password', enabled: true },
  ],
  samlEnabled: false,
  googleEnabled: false,
  githubEnabled: false,
  localEnabled: true,
};

const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Fetch auth configuration from the backend to discover available providers.
 */
export async function fetchAuthConfig(): Promise<AuthConfig> {
  try {
    const response = await fetch(`${baseUrl}/api/auth/config`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.warn('[AuthConfig] Failed to fetch auth config, using defaults');
      return DEFAULT_CONFIG;
    }

    const result = await response.json();

    if (!result.success || !result.data) {
      console.warn('[AuthConfig] Invalid auth config response, using defaults');
      return DEFAULT_CONFIG;
    }

    const data = result.data as any;

    // Build providers array from response
    const providers: AuthProviderConfig[] = [];

    if (data.localEnabled !== false) {
      providers.push({ id: 'local', name: 'Local Email/Password', enabled: true });
    }

    if (data.samlEnabled) {
      providers.push({ id: 'saml', name: 'Enterprise SSO (SAML)', enabled: true });
    }

    if (data.googleEnabled) {
      providers.push({ id: 'google', name: 'Google', enabled: true });
    }

    if (data.githubEnabled) {
      providers.push({ id: 'github', name: 'GitHub', enabled: true });
    }

    return {
      providers,
      samlEnabled: data.samlEnabled || false,
      googleEnabled: data.googleEnabled || false,
      githubEnabled: data.githubEnabled || false,
      localEnabled: data.localEnabled !== false,
    };
  } catch (error) {
    console.error('[AuthConfig] Error fetching auth config:', error);
    return DEFAULT_CONFIG;
  }
}

/**
 * Initialize auth config by fetching from backend. Call this once on app startup or page load.
 */
export async function initializeAuthConfig(): Promise<AuthConfig> {
  const config = await fetchAuthConfig();

  // Store in localStorage for persistence across page loads
  try {
    localStorage.setItem('iacgenie_auth_config', JSON.stringify(config));
  } catch (e) {
    console.warn('[AuthConfig] Could not persist auth config to localStorage');
  }

  return config;
}

/**
 * Load cached auth config from localStorage as a fallback.
 */
export function loadCachedAuthConfig(): AuthConfig | null {
  try {
    const cached = localStorage.getItem('iacgenie_auth_config');
    if (cached) {
      return JSON.parse(cached);
    }
  } catch (e) {
    console.warn('[AuthConfig] Could not load cached auth config');
  }
  return null;
}

export { baseUrl };
