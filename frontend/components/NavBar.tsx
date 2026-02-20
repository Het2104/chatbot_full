"use client";

/**
 * Navigation Bar Component
 * 
 * Shows login/register links for unauthenticated users
 * Shows user info and logout button for authenticated users
 */

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

export function NavBar() {
  const { isAuthenticated, user, logout } = useAuth();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <nav className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo/Brand */}
          <div className="flex items-center">
            <Link href="/" className="text-xl font-bold hover:text-gray-300 transition">
              🤖 AI Chatbot Platform
            </Link>
          </div>

          {/* Navigation Links */}
          <div className="flex items-center gap-6">
            {isAuthenticated ? (
              <>
                <span className="text-gray-300">
                  Hello, <span className="font-semibold">{user?.username}</span>
                  {user?.role === 'admin' && (
                    <span className="ml-2 text-xs bg-blue-600 px-2 py-1 rounded">Admin</span>
                  )}
                </span>
                <Link 
                  href="/" 
                  className="text-gray-300 hover:text-white transition"
                >
                  Chatbots
                </Link>
                {user?.role === 'admin' && (
                  <Link 
                    href="/admin" 
                    className="text-gray-300 hover:text-white transition"
                  >
                    Admin Panel
                  </Link>
                )}
                <button
                  onClick={handleLogout}
                  className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded-md transition"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link 
                  href="/login" 
                  className="text-gray-300 hover:text-white transition"
                >
                  Login
                </Link>
                <Link 
                  href="/register" 
                  className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-md transition"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
