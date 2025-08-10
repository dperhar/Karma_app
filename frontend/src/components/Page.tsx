'use client';

import { sdkReady } from '@/core/init';
// import { backButton } from '@telegram-apps/sdk-react';
import { useRouter } from 'next/navigation';
import { FC, ReactNode, useEffect, useState } from 'react';

import { Header } from '@/components/Header';

interface PageProps {
  children: ReactNode;
  back?: boolean;
  onBack?: () => void;
}

export const Page: FC<PageProps> = ({ children, back = false, onBack }) => {
  const router = useRouter();

  useEffect(() => {
    // Placeholder for any SDK-related logic if needed in the future
  }, [back, onBack, router]);

  return (
    <div className="min-h-screen bg-base-100">
      {children}
    </div>
  );
};