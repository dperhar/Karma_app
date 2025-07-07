import { mockTelegramEnv } from './mockTelegramEnv';

/**
 * Pre-initialize the application by setting up the mock environment
 * This MUST be called before React starts rendering to avoid race conditions
 */
export function preInitializeApp(): void {
  console.log('🚀 Pre-initializing app...');
  
  // Set up mock Telegram environment first (synchronously)
  mockTelegramEnv();
  
  console.log('✅ App pre-initialization complete');
}

// If we're in a browser environment, run pre-initialization immediately
if (typeof window !== 'undefined') {
  preInitializeApp();
} 