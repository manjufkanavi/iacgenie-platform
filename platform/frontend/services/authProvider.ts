import { LocalAuthProvider } from './localAuthProvider';

export interface IAuthProvider {
  signup(email: string, password: string): Promise<void>;
  login(email: string, password: string): Promise<void>;
  logout(): Promise<void>;
  sendEmailVerification(): Promise<void>;
  sendPasswordReset(email: string): Promise<void>;
}

export const getAuthProvider = (_provider: 'local') => {
  return new LocalAuthProvider();
};
