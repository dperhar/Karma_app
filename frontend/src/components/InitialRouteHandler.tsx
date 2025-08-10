'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';

function getStartParam() {
  if (typeof window === 'undefined') return null;

  // 1. Try to get from Telegram WebApp object
  if (window.Telegram?.WebApp?.initDataUnsafe?.start_param) {
    return window.Telegram.WebApp.initDataUnsafe.start_param;
  }

  // 2. Try to get from URL parameter
  const urlParams = new URLSearchParams(window.location.search);
  const startParam = urlParams.get('tgWebAppStartParam');
  if (startParam) {
    return startParam;
  }

  return null;
}

export function InitialRouteHandler() {
  const router = useRouter();
  const hasRedirected = useRef(false);

  useEffect(() => {
    // Get start parameter from all possible sources
    const startParam = getStartParam();
    console.log('WebApp start_param:', window.Telegram?.WebApp?.initDataUnsafe?.start_param);
    console.log('URL tgWebAppStartParam:', new URLSearchParams(window.location.search).get('tgWebAppStartParam'));
    console.log('Final start param:', startParam);

    if (startParam && !hasRedirected.current) {
      hasRedirected.current = true;
      console.log('Attempting to redirect to:', startParam);
      
      // Проверяем, содержит ли startParam ID спикера
      if (startParam.startsWith('speaker-')) {
        const speakerId = startParam.replace('speaker-', '');
        console.log('Redirecting to speaker questions page with speaker ID:', speakerId);
        router.replace(`/speaker-questions?speaker=${speakerId}`);
        return;
      }
      
      // Handle different route commands
      switch (startParam) {
        case 'schedule':
          console.log('Redirecting to schedule page');
          router.replace('/schedule');
          break;
        case 'ask-speaker':
        case 'speaker-questions':
          console.log('Redirecting to speaker questions page');
          router.replace('/speaker-questions');
          break;
        case 'voting':
          console.log('Redirecting to voting page');
          router.replace('/voting');
          break;
        // Add more routes as needed
        default:
          console.log('Unknown startParam:', startParam);
      }
    }
  }, [router]);

  return null; // This component doesn't render anything
} 