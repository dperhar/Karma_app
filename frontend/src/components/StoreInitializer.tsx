'use client';

import { useEffect, useState } from 'react';

interface StoreInitializerProps {
  children: React.ReactNode;
}

export function StoreInitializer({ children }: StoreInitializerProps) {
  const [isHydrated, setIsHydrated] = useState(false);
  
  // This ensures we don't try to use the store until after hydration
  useEffect(() => {
    setIsHydrated(true);
  }, []);

  if (!isHydrated) {
    // Return a simple loading state or nothing until hydrated
    return null;
  }

  return <>{children}</>;
} 