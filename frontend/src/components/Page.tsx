'use client';

import { sdkReady } from '@/core/init';
import { backButton } from '@telegram-apps/sdk-react';
import { useRouter } from 'next/navigation';
import { FC, ReactNode, useEffect, useState } from 'react';

interface PageProps {
  children: ReactNode;
  back?: boolean;
  onBack?: () => void;
}

export const Page: FC<PageProps> = ({ children, back = false, onBack }) => {
  const router = useRouter();
  const [isSdkReady, setIsSdkReady] = useState(sdkReady);
  
  // Listen for SDK ready event
  useEffect(() => {
    // If SDK is already ready, no need to listen for the event
    if (sdkReady) {
      setIsSdkReady(true);
      return;
    }

    // Otherwise, listen for the event
    const handleSdkReady = () => {
      setIsSdkReady(true);
    };
    
    window.addEventListener('telegram-sdk-ready', handleSdkReady);
    
    // Check again after a short delay in case we missed the event
    const timeoutId = setTimeout(() => {
      if (sdkReady) {
        setIsSdkReady(true);
      }
    }, 500);
    
    return () => {
      window.removeEventListener('telegram-sdk-ready', handleSdkReady);
      clearTimeout(timeoutId);
    };
  }, []);

  // Show/hide back button when SDK is ready
  useEffect(() => {
    if (isSdkReady && backButton.isSupported()) {
      try {
        if (back) {
          backButton.show();
        } else {
          backButton.hide();
        }
      } catch (error) {
        console.warn('Error toggling back button:', error);
      }
    }
  }, [back, isSdkReady]);

  // Set up back button click handler
  useEffect(() => {
    if (isSdkReady && backButton.isSupported() && back) {
      try {
        return backButton.onClick(() => {
          if (onBack) {
            onBack();
          } else {
            router.back();
          }
        });
      } catch (error) {
        console.warn('Error setting back button click handler:', error);
        return undefined;
      }
    }
    return undefined;
  }, [router, isSdkReady, onBack, back]);

  return (
    <div className="min-h-screen bg-base-100">
      {children}
    </div>
  );
};