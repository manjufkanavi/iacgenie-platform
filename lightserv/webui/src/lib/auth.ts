export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("lightsERP_token");
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("lightsERP_token", token);
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("lightsERP_token");
}

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

export function getAPIKey(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("lightsERP_api_key");
}

export function setAPIKey(key: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem("lightsERP_api_key", key);
}

export function clearAPIKey(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("lightsERP_api_key");
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  const apiKey = getAPIKey();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (apiKey) headers["X-API-Key"] = apiKey;
  return headers;
}

// Keycloak OAuth redirect
export const KEYCLOAK_AUTH_URL =
  "https://sso.iacgenie.com/realms/lightsERP/protocol/openid-connect/auth";
export const KEYCLOAK_CALLBACK_URL = "https://lightserp.iacgenie.com/auth/callback";
export const KEYCLOAK_CLIENT_ID = "lightserp-web";

export function startKeycloakLogin(): void {
  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    response_type: "code",
    redirect_uri: KEYCLOAK_CALLBACK_URL,
  });
  window.location.href = `${KEYCLOAK_AUTH_URL}?${params.toString()}`;
}

export function startKeycloakLogout(): void {
  clearAuthToken();
  clearAPIKey();
  const params = new URLSearchParams({
    post_logout_redirect_uri: "https://lightserp.iacgenie.com/login",
  });
  window.location.href = `https://sso.iacgenie.com/realms/lightsERP/protocol/openid-connect/logout?${params.toString()}`;
}
