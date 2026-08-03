export interface AuthProvider {
  signup(email: string, password: string, displayName?: string): Promise<any>;
  login(email: string, password: string): Promise<any>;
  logout(): Promise<void>;
  getCurrentUser(): Promise<User | null>;
}

export interface KeycloakAuthProvider {
  getLoginUrl(): string;
  handleCallback(code: string): Promise<any>;
  logout(token: string): Promise<any>;
}

// User type can be extended as needed for your app
export interface User {
  uid: string;
  email: string;
  role?: string;
  [key: string]: any;
} 