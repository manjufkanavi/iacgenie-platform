import { localAuthService } from './localAuthService';

// Shared helper for all API services
export const getAuthHeaders = () => {
  const token = localAuthService.getAuthToken();
  if (!token) throw new Error("User not authenticated - No token found");
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json"
  };
};

/**
 * Fetch wrapper that automatically refreshes the token on 401 and retries the request.
 * If refresh fails, clears auth and redirects to login.
 */
export async function retryWithFreshToken(
  url: string,
  options: RequestInit,
  getAuthHeadersFn?: () => Record<string, string>
): Promise<Response> {
  const response = await fetch(url, options);

  if (response.status === 401) {
    const refreshed = await localAuthService.refreshToken();
    if (refreshed) {
      const newHeaders = getAuthHeadersFn?.() || {
        Authorization: `Bearer ${localAuthService.getAuthToken()}`,
        "Content-Type": "application/json"
      };
      const retryOptions = { ...options, headers: newHeaders };
      return await fetch(url, retryOptions);
    }
    localAuthService.clearStorage();
    window.location.href = '/signin';
    throw new Error('Session expired. Please log in again.');
  }

  return response;
}
