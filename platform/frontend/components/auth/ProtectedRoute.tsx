import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/useAuthStore';

interface ProtectedRouteProps {
    children: React.ReactNode;
    roles?: string[];
}

interface PublicOnlyRouteProps {
    children: React.ReactNode;
}

/**
 * ProtectedRoute — renders children only if the user is authenticated.
 * Optionally restricts access to specific roles (e.g. ['admin']).
 * If not authenticated, redirects to /signin via window.location.
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, roles }) => {
    const navigate = useNavigate();
    const { isAuthenticated, user, refreshIfExpired } = useAuthStore();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        let cancelled = false;

        const checkAuth = async () => {
            if (cancelled) return;

            // If already authenticated and no role filter, allow immediately
            if (isAuthenticated && (!roles || roles.length === 0)) {
                setIsChecking(false);
                return;
            }

            // If not authenticated, try to refresh the token first
            if (!isAuthenticated) {
                const refreshed = await refreshIfExpired();
                if (cancelled) return;

                if (!refreshed) {
                    // Still not authenticated after refresh attempt — redirect to signin
                    navigate('/signin', { replace: true });
                    return;
                }
            }

            // Role-based check (only if user is now authenticated)
            if (roles && roles.length > 0) {
                const userRole = user?.roles?.global;
                if (!userRole || !roles.includes(userRole)) {
                    // User lacks required role — redirect to dashboard (or landing)
                    navigate('/dashboard', { replace: true });
                    return;
                }
            }

            setIsChecking(false);
        };

        checkAuth();

        return () => {
            cancelled = true;
        };
    }, [isAuthenticated, user, roles, navigate, refreshIfExpired]);

    // Show a loading spinner while checking auth
    if (isChecking) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
                    <p className="text-gray-600">Checking authentication…</p>
                </div>
            </div>
        );
    }

    return <>{children}</>;
};

/**
 * PublicOnlyRoute — renders children only if the user is NOT authenticated.
 * If already authenticated, redirects to /dashboard via window.location.
 */
export const PublicOnlyRoute: React.FC<PublicOnlyRouteProps> = ({ children }) => {
    const navigate = useNavigate();
    const { isAuthenticated, refreshIfExpired } = useAuthStore();
    const [isChecking, setIsChecking] = useState(true);

    useEffect(() => {
        let cancelled = false;

        const checkAuth = async () => {
            if (cancelled) return;

            // If already authenticated, redirect to dashboard
            if (isAuthenticated) {
                navigate('/dashboard', { replace: true });
                return;
            }

            // Not authenticated — try to refresh in case there's a stale token
            const refreshed = await refreshIfExpired();
            if (cancelled) return;

            // If refresh succeeded, user is now authenticated — redirect
            if (refreshed) {
                navigate('/dashboard', { replace: true });
                return;
            }

            setIsChecking(false);
        };

        checkAuth();

        return () => {
            cancelled = true;
        };
    }, [isAuthenticated, navigate, refreshIfExpired]);

    if (isChecking) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
                    <p className="text-gray-600">Checking authentication…</p>
                </div>
            </div>
        );
    }

    return <>{children}</>;
};

export default ProtectedRoute;
