"use client";

/**
 * Authentication Context
 * 
 * Provides global authentication state and methods for the entire application.
 * Uses React Context API to share auth state across components.
 * 
 * State managed:
 * - isAuthenticated: Whether user is logged in
 * - user: User object (id, email, username, role)
 * - token: JWT access token
 * 
 * Methods provided:
 * - login(email, password): Authenticate user
 * - logout(): Clear auth state
 * - register(userData): Create new account
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

// ============================================================================
// Types
// ============================================================================

interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
  role: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  role: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (userData: RegisterData) => Promise<void>;
  loading: boolean;
}

interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ============================================================================
// JWT Helper
// ============================================================================

/**
 * Decode JWT payload and return milliseconds remaining until token expires.
 * Returns -1 if token is invalid or already expired.
 */
function getTokenExpiryMs(token: string): number {
  try {
    const payload = token.split('.')[1];
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
    return decoded.exp * 1000 - Date.now();
  } catch {
    return -1;
  }
}

// ============================================================================
// Context Creation
// ============================================================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ============================================================================
// Provider Component
// ============================================================================

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const expiryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  // Cancel any pending auto-logout timer
  const cancelExpiryTimer = useCallback(() => {
    if (expiryTimerRef.current) {
      clearTimeout(expiryTimerRef.current);
      expiryTimerRef.current = null;
    }
  }, []);

  // Clear all auth state (localStorage token + React state)
  const clearAuthState = useCallback(() => {
    localStorage.removeItem('access_token');
    setIsAuthenticated(false);
    setUser(null);
    setRole(null);
    setToken(null);
  }, []);

  /**
   * Schedule automatic logout exactly when the JWT token expires.
   * Cancels any previously scheduled timer before setting a new one.
   */
  const scheduleTokenExpiry = useCallback((token: string) => {
    cancelExpiryTimer();

    const msUntilExpiry = getTokenExpiryMs(token);

    if (msUntilExpiry <= 0) {
      // Token already expired — clear state and redirect immediately
      clearAuthState();
      router.push('/login');
      return;
    }

    // Auto-logout exactly when the token expires
    expiryTimerRef.current = setTimeout(() => {
      expiryTimerRef.current = null;
      clearAuthState();
      router.push('/login');
    }, msUntilExpiry);
  }, [cancelExpiryTimer, clearAuthState, router]);

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('access_token');
      
      if (storedToken) {
        try {
          // Validate token by calling /auth/me endpoint
          const response = await fetch('http://127.0.0.1:8000/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });

          if (response.ok) {
            const userData = await response.json();
            setUser(userData);
            setRole(userData.role);
            setToken(storedToken);
            setIsAuthenticated(true);
            scheduleTokenExpiry(storedToken);
          } else {
            // Token expired or invalid
            localStorage.removeItem('access_token');
          }
        } catch (error) {
          console.error('Failed to validate token:', error);
          localStorage.removeItem('access_token');
        }
      }
      
      setLoading(false);
    };

    initializeAuth();
  }, [scheduleTokenExpiry]);

  // Listen for logout events from API client (e.g. 401 on protected routes)
  useEffect(() => {
    const handleLogoutEvent = () => {
      cancelExpiryTimer();
      clearAuthState();
      router.push('/login');
    };

    window.addEventListener('auth:logout', handleLogoutEvent);
    return () => window.removeEventListener('auth:logout', handleLogoutEvent);
  }, [router]);

  /**
   * Login user with email and password
   */
  const login = async (email: string, password: string) => {
    const response = await fetch('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Login failed');
    }

    const data: LoginResponse = await response.json();
    
    // Store token in localStorage
    localStorage.setItem('access_token', data.access_token);
    
    // Update state
    setToken(data.access_token);
    setUser(data.user);
    setRole(data.user.role);
    setIsAuthenticated(true);

    // Start countdown — auto-logout when token expires
    scheduleTokenExpiry(data.access_token);
  };

  /**
   * Logout user and clear all auth state
   */
  const logout = () => {
    cancelExpiryTimer();
    clearAuthState();
    router.push('/login');
  };

  /**
   * Register new user account
   */
  const register = async (userData: RegisterData) => {
    const response = await fetch('http://127.0.0.1:8000/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || 'Registration failed');
    }

    // Registration successful - user can now login
    // Note: Not auto-logging in, user must login after registration
  };

  const value: AuthContextType = {
    isAuthenticated,
    user,
    token,
    role,
    login,
    logout,
    register,
    loading
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ============================================================================
// Custom Hook
// ============================================================================

/**
 * Hook to access auth context
 * 
 * @throws Error if used outside AuthProvider
 */
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  
  return context;
}
