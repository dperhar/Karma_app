'use client';

import { useRouter } from 'next/navigation';
import { useCallback } from 'react';

export function useLocale() {
  const router = useRouter();

  const setLocale = useCallback((locale: string) => {
    // In this case, we're just using the locale from Telegram's user data
    // No need to actually change the locale since it's handled by the server
    console.log('Setting locale:', locale);
  }, []);

  return { setLocale };
} 