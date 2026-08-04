import { User } from './store/useAppStore';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignupCredentials {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
  displayName?: string;
}

export interface AuthResponse {
  user: User;
  token: string;
  expiresIn?: number;
}

export interface SignupResult {
  success: boolean;
  user?: User;
  token?: string;
  message?: string;
  error?: string;
  otpToken?: string;  // OTP token for email verification
}

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
  error?: {
    code: string;
    message: string;
    statusCode: number;
  };
}

class LocalAuthService {
  private currentUser: User | null = null;
  private authToken: string | null = null;
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    this.loadFromStorage();
  }

  private loadFromStorage() {
    try {
      const storedUser = localStorage.getItem('iacgenie_user');
      const storedToken = localStorage.getItem('iacgenie_token');
      
      if (storedUser && storedToken) {
        this.currentUser = JSON.parse(storedUser);
        this.authToken = storedToken;
      }
    } catch (error) {
      console.error('Error loading auth data from storage:', error);
      this.clearStorage();
    }
  }

  public clearStorage() {
    localStorage.removeItem('iacgenie_user');
    localStorage.removeItem('iacgenie_token');
    localStorage.removeItem('iacgenie-auth');
    this.currentUser = null;
    this.authToken = null;
  }

  private handleAuthError(error: any): { userFriendlyMessage: string; technicalMessage: string } {
    let userFriendlyMessage = 'An unexpected error occurred';
    let technicalMessage = error.message || 'Unknown error';

    // Extract the actual error message and code from API response format
    const errorMessage = typeof error === 'object' ? (error.message || error.body?.message || error.error?.message || JSON.stringify(error)) : String(error);
    const errorCode = typeof error === 'object' ? (error.code || error.body?.code || error.error?.code || '') : '';

    if (errorCode.includes('EMAIL_NOT_VERIFIED') || errorMessage.includes('Please verify your email') || errorMessage.includes('Account is not fully set up') || errorMessage.includes('not fully set up')) {
      userFriendlyMessage = 'Please verify your email before signing in. Check your inbox for a verification link.';
    } else if (errorCode.includes('INVALID_CREDENTIALS') || errorMessage.includes('Invalid email or password')) {
      userFriendlyMessage = 'Invalid email or password';
    } else if (errorCode.includes('EMAIL_ALREADY_EXISTS') || errorCode.includes('EMAIL_EXISTS') || errorMessage.includes('Email already registered') || errorMessage.includes('User already exists')) {
      userFriendlyMessage = 'An account with this email already exists. Please log in instead.';
    } else if (errorCode.includes('INVALID_TOKEN') || errorMessage.includes('Token is invalid')) {
      userFriendlyMessage = 'Your session has expired. Please sign in again';
    } else if (errorCode.includes('NETWORK_ERROR')) {
      userFriendlyMessage = 'Network error. Please check your connection';
    } else if (errorCode.includes('RATE_LIMITED') || errorMessage.includes('Too many attempts')) {
      userFriendlyMessage = 'Too many attempts. Please try again later';
    } else if (errorCode.includes('ACCOUNT_DISABLED')) {
      userFriendlyMessage = 'This account has been disabled';
    } else if (errorCode.includes('WEAK_PASSWORD')) {
      userFriendlyMessage = 'Password does not meet requirements';
    } else if (errorCode.includes('INVALID_EMAIL')) {
      userFriendlyMessage = 'Invalid email format';
    } else if (errorCode.includes('USER_NOT_FOUND')) {
      userFriendlyMessage = 'User not found';
    } else if (errorCode.includes('INTERNAL_ERROR')) {
      userFriendlyMessage = 'An internal server error occurred. Please try again later';
    } else if (errorMessage.includes('Internal server error')) {
      userFriendlyMessage = 'An internal server error occurred. Please try again later';
    } else if (errorMessage.includes('Failed to create user')) {
      userFriendlyMessage = 'Failed to create account. Please try again later';
    } else if (errorMessage.includes('Database not initialized')) {
      userFriendlyMessage = 'Authentication service is temporarily unavailable. Please try again later';
    }

    return { userFriendlyMessage, technicalMessage };
  }

  async login(credentials: LoginCredentials): Promise<User> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'login',
          email: credentials.email,
          password: credentials.password
        }),
      });

      const result = await response.json();

      // Backend returns 503 with AUTH_FLOW_UNAVAILABLE when ROPC is disabled.
      // Redirect the browser to the Keycloak OAuth code flow instead.
      if (response.status === 503 && result?.error?.code === 'AUTH_FLOW_UNAVAILABLE') {
        const message = result.error?.message || '';
        const ssoMatch = message.match(/SSO at (https?:\/\/[^\s.]+\S*)/);
        if (ssoMatch) {
          window.location.href = ssoMatch[1];
        } else {
          window.location.href = `${this.baseUrl}/api/auth/keycloak/login`;
        }
        // Never resolve — the page will navigate away
        throw new Error('Redirecting to SSO login');
      }

      if (!response.ok) {
        // Extract error details from structured response
        const errorMessage = result.error?.message || result.message || `HTTP ${response.status}`;
        const errorCode = result.error?.code || '';

        // Create a combined error object that handleAuthError can process
        const authError = this.handleAuthError({
          message: errorMessage,
          code: errorCode,
          error: result.error || {}
        });
        throw new Error(authError.userFriendlyMessage);
      }

      if (!result.data) {
        throw new Error('Invalid response from server');
      }

      const userData = result.data.user || {};
      const token = result.data.token;

      if (!token) {
        throw new Error('No authentication token received');
      }

      // Create user object
      const user: User = {
        name: userData.displayName || userData.name || credentials.email.split('@')[0],
        email: credentials.email,
        avatarUrl: userData.avatarUrl || `https://i.pravatar.cc/150?u=${credentials.email}`,
        roles: userData.roles || { global: userData.role || 'user', projects: {} },
        uid: userData.uid || undefined
      };

      // Fetch roles from backend (in case they weren't in the login response)
      try {
        const rolesResponse = await fetch(`${this.baseUrl}/api/auth/roles`, { 
          headers: { Authorization: `Bearer ${token}` } 
        });
        if (rolesResponse.ok) {
          const rolesData = await rolesResponse.json();
          user.roles = rolesData.roles;
        }
      } catch (e) {
        console.log('Could not fetch roles:', e);
      }

      this.currentUser = user;
      this.authToken = token;
      localStorage.setItem('iacgenie_user', JSON.stringify(user));
      localStorage.setItem('iacgenie_token', token);

      return user;
    } catch (error: any) {
      console.error('Local auth login failed:', error);
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }

  async signup(credentials: SignupCredentials): Promise<SignupResult> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action: 'signup',
          email: credentials.email,
          password: credentials.password,
          displayName: credentials.displayName,
          firstName: credentials.firstName,
          lastName: credentials.lastName,
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        // Extract error details from structured response
        const errorMessage = result.error?.message || result.message || `HTTP ${response.status}`;
        const errorCode = result.error?.code || '';
        
        // Create a combined error object that handleAuthError can process
        const authError = this.handleAuthError({
          message: errorMessage,
          code: errorCode,
          error: result.error || {}
        });
        throw new Error(authError.userFriendlyMessage);
      }

      // Parse and return the signup result
      console.log('[Signup] Full response:', JSON.stringify(result, null, 2));

      const userData = result.data?.user || (result.user && typeof result.user === 'object' ? result.user : undefined);
      const message = result.data?.message || result.message;

      if (result.success) {
        return {
          success: true,
          user: userData ? {
            name: userData.displayName || userData.name || credentials.email.split('@')[0],
            email: credentials.email,
            avatarUrl: userData.avatarUrl || `https://i.pravatar.cc/150?u=${credentials.email}`,
            roles: userData.roles || { global: userData.role || 'user', projects: {} },
            uid: userData.uid || undefined
          } : undefined,
          message: message || 'Account created. Check your email for a verification link.',
        };
      }

      return { success: false, message: message || 'Signup failed' };

    } catch (error: any) {
      // Re-throw without double-wrapping: the error message is already user-friendly
      // from the handleAuthError call inside the try block.
      console.error('Local auth signup failed:', error);
      throw error;
    }
  }

  async logout(): Promise<void> {
    this.clearStorage();
  }

  getCurrentUser(): User | null {
    this.loadFromStorage();
    return this.currentUser;
  }

  getAuthToken(): string | null {
    if (this.authToken) return this.authToken;
    
    let token = localStorage.getItem('iacgenie_token');
    if (!token) {
      try {
        const authStoreStr = localStorage.getItem('iacgenie-auth');
        if (authStoreStr) {
          const authStore = JSON.parse(authStoreStr);
          if (authStore?.state?.token) {
            token = authStore.state.token;
            // Heal the storage
            this.authToken = token;
            localStorage.setItem('iacgenie_token', token ?? '');
          }
        }
      } catch (e) {
        // ignore parsing errors
      }
    } else {
      this.authToken = token;
    }
    
    return token;
  }

  isAuthenticated(): boolean {
    return !!this.currentUser && !!this.authToken;
  }

  /**
   * Verify OTP token and login user without password for password reset flow
   * 
   * This method calls the /api/auth/verify-otp-and-login endpoint which:
   * 1. Validates the OTP token (6 digits)
   * 2. Returns user data and auth token on success
   * 3. Does NOT require password strength validation during OTP step
   */
  async verifyOtpAndLogin(token: string, otp: string): Promise<User> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/verify-otp-and-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          otp
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        // Extract error details from structured response
        const errorMessage = result.error?.message || result.message || `HTTP ${response.status}`;
        const errorCode = result.error?.code || '';
        
        // Create a combined error object that handleAuthError can process
        const authError = this.handleAuthError({
          message: errorMessage,
          code: errorCode,
          error: result.error || {}
        });
        throw new Error(authError.userFriendlyMessage);
      }

      if (!result.data) {
        throw new Error('Invalid response from server');
      }

      const userData = result.data.user || {};
      const tokenData = result.data.token;

      if (!userData.email) {
        throw new Error('Invalid response from server - missing user data');
      }

      // Create user object
      const user: User = {
        name: userData.displayName || userData.name || userData.email.split('@')[0],
        email: userData.email,
        avatarUrl: userData.avatarUrl || `https://i.pravatar.cc/150?u=${userData.email}`,
        roles: userData.roles || { global: userData.role || 'user', projects: {} },
        uid: userData.uid || undefined
      };

      // Fetch roles from backend (in case they weren't in the response)
      if (tokenData) {
        try {
          const rolesResponse = await fetch(`${this.baseUrl}/api/auth/roles`, { 
            headers: { Authorization: `Bearer ${tokenData}` } 
          });
          if (rolesResponse.ok) {
            const rolesData = await rolesResponse.json();
            user.roles = rolesData.roles;
          }
        } catch (e) {
          console.log('Could not fetch roles after OTP verification:', e);
        }

        this.currentUser = user;
        this.authToken = tokenData;
        localStorage.setItem('iacgenie_user', JSON.stringify(user));
        localStorage.setItem('iacgenie_token', tokenData);
      }

      return user;
    } catch (error: any) {
      console.error('Verify OTP and login failed:', error);
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }

  async verifyToken(token: string): Promise<AuthResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/token/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error?.message || 'Token verification failed');
      }

      if (result.data?.valid && result.data.user) {
        const userData = result.data.user;
        const user: User = {
          name: userData.displayName || userData.name || userData.email?.split('@')[0] || 'User',
          email: userData.email,
          avatarUrl: userData.photoURL || `https://i.pravatar.cc/150?u=${userData.email}`,
          roles: { global: userData.role || 'user', projects: {} }
        };

        this.currentUser = user;
        this.authToken = token;
        localStorage.setItem('iacgenie_user', JSON.stringify(user));
        localStorage.setItem('iacgenie_token', token);

        return { user, token };
      }

      throw new Error('Invalid token');
    } catch (error: any) {
      console.error('Token verification failed:', error);
      this.clearStorage();
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }

  /**
   * Refresh the current JWT token by calling the backend refresh endpoint.
   * Returns the new token if successful, null otherwise.
   */
  async refreshToken(): Promise<string | null> {
    const token = this.getAuthToken();
    if (!token) return null;
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/token/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error?.message || result.message || `HTTP ${response.status}`);
      }

      const newToken = result.data?.token;
      if (newToken) {
        this.authToken = newToken;
        localStorage.setItem('iacgenie_token', newToken);
        return newToken;
      }

      throw new Error('No new token returned');
    } catch (error: any) {
      console.error('Token refresh failed:', error);
      this.clearStorage();
      return null;
    }
  }

  async requestPasswordResetOTP(email: string): Promise<{ token?: string; message?: string }> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/forgot-password-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error?.message || result.message || `HTTP ${response.status}`);
      }
      
      // Return token and message for frontend to use
      return {
        token: result.data?.token,
        message: result.message || 'OTP sent successfully'
      };
    } catch (error: any) {
      console.error('Request password reset OTP failed:', error);
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }

  // For password reset with OTP, the frontend passes OTP as password
  async verifyOtpAndResetPassword(token: string, newPasswordOrOtp: string): Promise<User> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/reset-password-with-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          token,
          new_password: newPasswordOrOtp
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        // Extract error details from structured response
        const errorMessage = result.error?.message || result.message || `HTTP ${response.status}`;
        const errorCode = result.error?.code || '';
        
        // Create a combined error object that handleAuthError can process
        const authError = this.handleAuthError({
          message: errorMessage,
          code: errorCode,
          error: result.error || {}
        });
        throw new Error(authError.userFriendlyMessage);
      }

      if (!result.data) {
        throw new Error('Invalid response from server');
      }

      const userData = result.data.user || {};
      const tokenData = result.data.token;

      if (!userData.email) {
        throw new Error('Invalid response from server - missing user data');
      }

      // Create user object
      const user: User = {
        name: userData.displayName || userData.name || userData.email.split('@')[0],
        email: userData.email,
        avatarUrl: userData.avatarUrl || `https://i.pravatar.cc/150?u=${userData.email}`,
        roles: userData.roles || { global: userData.role || 'user', projects: {} },
        uid: userData.uid || undefined
      };

      // Fetch roles from backend (in case they weren't in the response)
      if (tokenData) {
        try {
          const rolesResponse = await fetch(`${this.baseUrl}/api/auth/roles`, { 
            headers: { Authorization: `Bearer ${tokenData}` } 
          });
          if (rolesResponse.ok) {
            const rolesData = await rolesResponse.json();
            user.roles = rolesData.roles;
          }
        } catch (e) {
          console.log('Could not fetch roles after password reset:', e);
        }

        this.currentUser = user;
        this.authToken = tokenData;
        localStorage.setItem('iacgenie_user', JSON.stringify(user));
        localStorage.setItem('iacgenie_token', tokenData);
      }

      return user;
    } catch (error: any) {
      console.error('Verify OTP and reset password failed:', error);
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }

  async resetPassword(email: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email
        }),
      });

      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error?.message || result.message || `HTTP ${response.status}`);
      }
    } catch (error: any) {
      console.error('Password reset failed:', error);
      throw new Error(this.handleAuthError(error).userFriendlyMessage);
    }
  }
}

// Export singleton instance
export const localAuthService = new LocalAuthService();
export default localAuthService;