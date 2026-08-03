/**
 * Centralized API Client for Iacgenie AI
 * Handles authentication, token management, and API requests
 */

import { getAuthHeaders } from "./authHeaders";

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: {
    code: string;
    message: string;
    statusCode: number;
    details?: any;
  };
  timestamp?: string;
}

export interface ApiError {
  code: string;
  message: string;
  statusCode: number;
  details?: any;
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  }

  /**
   * Get stored authentication token
   */
  private getStoredToken(): string | null {
    return localStorage.getItem('iacgenie_token');
  }

  /**
   * Store authentication token
   */
  private storeToken(token: string): void {
    localStorage.setItem('iacgenie_token', token);
  }

  /**
   * Clear stored authentication data
   */
  private clearAuthData(): void {
    localStorage.removeItem('iacgenie_token');
    localStorage.removeItem('iacgenie_user');
  }

  /**
   * Validate token format (length and structure)
   */
  private isValidToken(token: string | null): boolean {
    return !!token && token.length > 100 && token.split('.').length === 3;
  }

  /**
   * Handle API response and extract data
   */
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');

    if (!response.ok) {
      let errorData: any = {};
      
      if (isJson) {
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: 'Failed to parse error response' };
        }
      } else {
        errorData = { message: response.statusText || 'Request failed' };
      }

      return {
        success: false,
        error: {
          code: errorData.error?.code || 'API_ERROR',
          message: errorData.error?.message || errorData.message || 'Request failed',
          statusCode: response.status,
          details: errorData.error?.details || errorData
        }
      };
    }

    if (isJson) {
      try {
        const data = await response.json();
        return {
          success: true,
          data: data.data || data,
          message: data.message,
          timestamp: data.timestamp
        };
      } catch {
        return {
          success: false,
          error: {
            code: 'PARSE_ERROR',
            message: 'Failed to parse response',
            statusCode: response.status
          }
        };
      }
    }

    return {
      success: true,
      data: await response.text() as any,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Make authenticated API request with automatic token refresh
   */
  async request<T>(
    endpoint: string,
    options: RequestInit = {},
    timeoutMs: number = 10000 // 10 seconds default
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    let headers = getAuthHeaders();

    // Validate token before use
    if (!this.isValidToken(headers['Authorization']?.replace('Bearer ', ''))) {
      this.clearAuthData();
      return {
        success: false,
        error: {
          code: 'INVALID_TOKEN',
          message: 'Invalid or missing authentication token. Please sign in again.',
          statusCode: 401
        }
      };
    }

    // Merge headers
    const requestHeaders = {
      ...headers,
      ...options.headers,
    };

    // Add AbortController for global timeout
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        headers: requestHeaders,
        signal: controller.signal,
      });
      clearTimeout(timeout);

      // Handle 401 Unauthorized - attempt token refresh and retry
      if (response.status === 401) {
        const { localAuthService } = await import('./localAuthService');
        const refreshed = await localAuthService.refreshToken();
        if (refreshed) {
          const newToken = localAuthService.getAuthToken();
          if (newToken) {
            const retryHeaders = {
              ...headers,
              Authorization: `Bearer ${newToken}`,
              ...options.headers,
            };
            const retryController = new AbortController();
            const retryTimeout = setTimeout(() => retryController.abort(), timeoutMs);
            try {
              const retryResponse = await fetch(url, {
                ...options,
                headers: retryHeaders,
                signal: retryController.signal,
              });
              clearTimeout(retryTimeout);
              return this.handleResponse<T>(retryResponse);
            } catch (retryError: any) {
              clearTimeout(retryTimeout);
              if (retryError.name === 'AbortError') {
                return {
                  success: false,
                  error: {
                    code: 'TIMEOUT',
                    message: 'Request timed out',
                    statusCode: 408
                  }
                };
              }
              return {
                success: false,
                error: {
                  code: 'NETWORK_ERROR',
                  message: retryError.message || 'Network error',
                  statusCode: 500
                }
              };
            }
          }
        }
        // Refresh failed or no new token — clear auth and redirect
        this.clearAuthData();
        return {
          success: false,
          error: {
            code: 'AUTHENTICATION_REQUIRED',
            message: 'Authentication required. Please sign in again.',
            statusCode: 401
          }
        };
      }

      return this.handleResponse<T>(response);
    } catch (error: any) {
      clearTimeout(timeout);
      if (error.name === 'AbortError') {
        return {
          success: false,
          error: {
            code: 'TIMEOUT',
            message: 'Request timed out',
            statusCode: 408
          }
        };
      }
      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: error.message || 'Network error',
          statusCode: 500
        }
      };
    }
  }

  /**
   * Perform actual token refresh
   */
  /**
   * Authenticate user with email and password
   */
  async authenticate(email: string, password: string): Promise<ApiResponse<{
    token: string;
    refreshToken?: string;
    user: {
      uid: string;
      email: string;
      emailVerified: boolean;
      displayName?: string;
      photoURL?: string;
    };
    expiresIn: number;
  }>> {
    const response = await fetch(`${this.baseUrl}/auth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const result = await this.handleResponse<{
      token: string;
      refreshToken?: string;
      user: {
        uid: string;
        email: string;
        emailVerified: boolean;
        displayName?: string;
        photoURL?: string;
      };
      expiresIn: number;
    }>(response);
    
    if (result.success && result.data) {
      // Store tokens
      this.storeToken(result.data.token);
      if (result.data.refreshToken) {
        localStorage.setItem('iacgenie_refresh_token', result.data.refreshToken);
      }
      
      // Store user data
      localStorage.setItem('iacgenie_user', JSON.stringify(result.data.user));
    }

    return result;
  }

  /**
   * Verify current token
   */
  async verifyToken(): Promise<ApiResponse<{
    valid: boolean;
    user: any;
    claims: any;
  }>> {
    const token = this.getStoredToken();
    if (!token) {
      return {
        success: false,
        error: {
          code: 'NO_TOKEN',
          message: 'No authentication token found',
          statusCode: 401
        }
      };
    }

    return this.request('/auth/token/verify', {
      method: 'POST',
      body: JSON.stringify({ token })
    });
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    try {
      // Call logout endpoint if available
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout API call failed:', error);
    } finally {
      // Always clear local data
      this.clearAuthData();
      localStorage.removeItem('iacgenie_refresh_token');
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.getStoredToken() !== null;
  }

  /**
   * Get current user from storage
   */
  getCurrentUser(): any {
    const userData = localStorage.getItem('iacgenie_user');
    if (userData) {
      try {
        return JSON.parse(userData);
      } catch {
        return null;
      }
    }
    return null;
  }
}

// Export singleton instance
export const apiClient = new ApiClient(); 