'use client';

import { useEffect, useState } from 'react';
import { TelegramAuthModal } from '../TelegramAuthModal/TelegramAuthModal';

interface RootProps {
  children: React.ReactNode;
}

// Helper function to restore authenticated Telegram environment from stored data
const restoreAuthenticatedEnvironment = (userId: number) => {
  try {
    console.log('🔄 Restoring authenticated session for user:', userId);
    
    // Simply mark the session as authenticated since Telethon handles the actual connection
    if (typeof window !== 'undefined') {
      sessionStorage.setItem("env-authenticated", "1");
      sessionStorage.setItem("authenticated-user-id", userId.toString());
    }

    console.log('✅ Authenticated session restored for user:', userId);
    return true;
  } catch (error) {
    console.error('❌ Failed to restore authenticated session:', error);
    return false;
  }
};

// Helper function to check authentication synchronously
const checkAuthState = () => {
  try {
    // Check if we have a session cookie
    const hasSessionCookie = document.cookie.includes('karma_session=');
    
    // Check localStorage for persistent auth data
    let hasPersistentAuth = false;
    
    try {
      const storedAuth = localStorage.getItem('karma_auth');
      if (storedAuth) {
        const authData = JSON.parse(storedAuth);
        const now = Date.now();
        
        // Check if stored auth is still valid (not expired)
        if (authData.expiresAt && now < authData.expiresAt) {
          hasPersistentAuth = true;
        }
      }
    } catch (e) {
      // Invalid auth data, ignore
    }
    
    // Also check if environment has been authenticated in this session
    const isEnvAuthenticated = typeof window !== 'undefined' && 
      sessionStorage.getItem("env-authenticated") === "1";
    
    return hasSessionCookie || hasPersistentAuth || isEnvAuthenticated;
  } catch (error) {
    return false;
  }
};

export function Root({ children }: RootProps) {
  // Check authentication state immediately to set correct initial state
  const initialAuthState = typeof window !== 'undefined' ? checkAuthState() : false;
  
  const [isAuthenticated, setIsAuthenticated] = useState(initialAuthState);
  const [showAuthModal, setShowAuthModal] = useState(!initialAuthState);
  
  // Debug logging for auth state
  console.log('🔍 Root component - Initial auth state:', {
    initialAuthState,
    isAuthenticated,
    showAuthModal
  });

  useEffect(() => {
    // Check for authentication state with persistence
    const checkAuth = () => {
      try {
        // Check if we have a session cookie
        const hasSessionCookie = document.cookie.includes('karma_session=');
        
        // Check localStorage for persistent auth data
        let hasPersistentAuth = false;
        let authData = null;
        
        try {
          const storedAuth = localStorage.getItem('karma_auth');
          if (storedAuth) {
            authData = JSON.parse(storedAuth);
            const now = Date.now();
            
            // Check if stored auth is still valid (not expired)
            if (authData.expiresAt && now < authData.expiresAt) {
              hasPersistentAuth = true;
              console.log('✅ Found valid persistent authentication:', {
                userId: authData.userId,
                authenticatedAt: new Date(authData.authenticatedAt).toLocaleString(),
                expiresAt: new Date(authData.expiresAt).toLocaleString()
              });
            } else {
              console.log('⚠️ Stored authentication expired, clearing...');
              localStorage.removeItem('karma_auth');
              sessionStorage.removeItem('env-authenticated');
            }
          }
        } catch (e) {
          console.warn('Failed to parse stored auth data:', e);
          localStorage.removeItem('karma_auth');
        }
        
        // Also check if environment has been authenticated in this session
        const isEnvAuthenticated = typeof window !== 'undefined' && 
          sessionStorage.getItem("env-authenticated") === "1";
        
        const isAuthenticated = hasSessionCookie || hasPersistentAuth || isEnvAuthenticated;
        
        // If we have persistent auth but no environment auth, restore the environment
        if (hasPersistentAuth && !isEnvAuthenticated && authData) {
          console.log('🔄 Restoring authenticated environment from persistent storage...');
          restoreAuthenticatedEnvironment(authData.userId);
        }
        
        setIsAuthenticated(isAuthenticated);
        setShowAuthModal(!isAuthenticated);
        
        if (isAuthenticated) {
          console.log('✅ User is authenticated:', {
            cookie: hasSessionCookie,
            persistent: hasPersistentAuth,
            session: isEnvAuthenticated
          });
        }
      } catch (error) {
        console.error('Error checking authentication:', error);
        setIsAuthenticated(false);
        setShowAuthModal(true);
      }
    };

    checkAuth();
    
    // Recheck auth state when page becomes visible (for session changes)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        checkAuth();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
    setShowAuthModal(false);
    
    // Force a page reload to ensure the updated Telegram environment is fully applied
    // This ensures all hooks and components re-initialize with the new authenticated context
    setTimeout(() => {
      window.location.reload();
    }, 100);
  };

  // Function to handle logout and clear all persistent data
  const handleLogout = () => {
    try {
      // Clear localStorage auth data
      localStorage.removeItem('karma_auth');
      
      // Clear sessionStorage
      sessionStorage.removeItem('env-authenticated');
      sessionStorage.removeItem('authenticated-user-id');
      
      // Clear session cookie
      document.cookie = 'karma_session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Lax';
      
      console.log('🚪 User logged out, all persistent data cleared');
      
      // Reset authentication state
      setIsAuthenticated(false);
      setShowAuthModal(true);
      
      // Reload to ensure clean state
      window.location.reload();
    } catch (error) {
      console.error('Error during logout:', error);
    }
  };

  // Expose logout function globally for debugging/testing
  if (typeof window !== 'undefined') {
    (window as any).logout = handleLogout;
  }

  console.log('🎯 Root component render decision:', {
    showAuthModal,
    isAuthenticated,
    willShowModal: showAuthModal
  });

  if (showAuthModal) {
    console.log('🚨 Rendering auth modal because showAuthModal is true');
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <TelegramAuthModal 
          isOpen={true} 
          onClose={() => setShowAuthModal(false)} 
          initDataRaw="mock_init_data_for_dev"
          onSuccess={handleAuthSuccess}
        />
      </div>
    );
  }

  console.log('✅ Rendering main app (no auth modal)');

  return (
    <div className="min-h-screen bg-gray-900">
      {children}
    </div>
  );
}