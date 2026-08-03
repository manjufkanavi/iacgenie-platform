import { IAuthProvider } from './authProvider';
import { localAuthService } from './localAuthService';

export class LocalAuthProvider implements IAuthProvider {
    async signup(email: string, password: string): Promise<void> {
        await localAuthService.signup({ email, password });
    }

    async login(email: string, password: string): Promise<void> {
        await localAuthService.login({ email, password });
    }

    async logout(): Promise<void> {
        await localAuthService.logout();
    }

    async sendEmailVerification(): Promise<void> {
        // Email verification is handled automatically during signup
        throw new Error('Email verification is handled automatically during signup');
    }

    async sendPasswordReset(email: string): Promise<void> {
        // Password reset is handled via backend endpoint
        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${baseUrl}/api/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to send password reset email');
        }
    }
}
