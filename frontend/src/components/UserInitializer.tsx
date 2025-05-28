'use client';

import { useUserStore } from '@/store/userStore';
import { useEffect } from 'react';

export const UserInitializer = () => {
  const { fetchUser } = useUserStore();

  useEffect(() => {
    const timer = setTimeout(() => {
      if (fetchUser) {
        fetchUser();
      }
    }, 0);

    return () => clearTimeout(timer);
  }, [fetchUser]);

  return null;
}; 