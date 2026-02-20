"use client";

/**
 * Protected Route Wrapper Component
 * 
 * Higher-Order Component that wraps pages requiring authentication.
 * Redirects to login if user is not authenticated.
 * Optionally restricts access by role.
 * 
 * Usage:
 *   export default withAuth(YourPage);
 *   export default withAuth(AdminPage, ['admin']);
 */

import { useEffect, ComponentType } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

/**
 * Wraps a component with authentication protection
 * 
 * @param Component - Component to protect
 * @param allowedRoles - Optional array of roles allowed to access (default: all authenticated users)
 * @returns Protected component
 */
export function withAuth<P extends object>(
  Component: ComponentType<P>,
  allowedRoles?: string[]
) {
  return function ProtectedRoute(props: P) {
    const { isAuthenticated, role, loading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!loading) {
        // Redirect to login if not authenticated
        if (!isAuthenticated) {
          router.push('/login');
          return;
        }

        // Check role-based authorization if roles are specified
        if (allowedRoles && role && !allowedRoles.includes(role)) {
          // User doesn't have required role
          router.push('/unauthorized');
        }
      }
    }, [isAuthenticated, role, loading, router]);

    // Show loading state while checking auth
    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-lg">Loading...</div>
        </div>
      );
    }

    // Don't render component if not authenticated or unauthorized
    if (!isAuthenticated) {
      return null;
    }

    if (allowedRoles && role && !allowedRoles.includes(role)) {
      return null;
    }

    // User is authenticated and authorized
    return <Component {...props} />;
  };
}

/**
 * Hook-based alternative for protecting pages
 * Call this at the top of your component
 * 
 * Usage:
 *   useProtectedRoute();
 *   useProtectedRoute(['admin']);
 */
export function useProtectedRoute(allowedRoles?: string[]) {
  const { isAuthenticated, role, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push('/login');
        return;
      }

      if (allowedRoles && role && !allowedRoles.includes(role)) {
        router.push('/unauthorized');
      }
    }
  }, [isAuthenticated, role, loading, allowedRoles, router]);

  return { isAuthenticated, role, loading };
}
