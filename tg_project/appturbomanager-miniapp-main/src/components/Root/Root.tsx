'use client';

import {
  initData,
  miniApp,
  swipeBehavior,
  useLaunchParams,
  useSignal,
} from '@telegram-apps/sdk-react';
import { AppRoot } from '@telegram-apps/telegram-ui';
import { type PropsWithChildren, useEffect, useRef, useState } from 'react';

import { ErrorBoundary } from '@/components/ErrorBoundary';
import { ErrorPage } from '@/components/ErrorPage';
import { Preloader } from '@/components/Preloader/Preloader';
import { useLocale } from '@/core/i18n/useLocale';
import { init } from '@/core/init';
import { useDidMount } from '@/hooks/useDidMount';
import { useTelegramMock } from '@/hooks/useTelegramMock';

import './styles.css';

// Global initialization flag to prevent double initialization in strict mode
let appInitialized = false;

function RootInner({ children }: PropsWithChildren) {
  const isDev = process.env.NODE_ENV === 'development';
  console.log('isDev', isDev);
  
  // Mock Telegram environment in development mode
  // This must be called before any other Telegram SDK hooks
  if (isDev) {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    useTelegramMock();
  }
  
  const lp = useLaunchParams();
  console.log("lp", lp);

  const debug = isDev || lp.startParam === 'debug';

  // Initialize the library only once across all renders
  useEffect(() => {
    if (!appInitialized) {
      appInitialized = true;
      init(debug);
      
      // Mount the swipeBehavior component before using its methods
      swipeBehavior.mount();
      // Disable vertical swipe after SDK initialization
      swipeBehavior.disableVertical();
    }
  }, [debug]);

  const isDark = useSignal(miniApp.isDark);
  const initDataUser = useSignal(initData.user);
  const initDataRaw = useSignal(initData.raw);
  const [isInitialized, setIsInitialized] = useState(false);
  const initAttempted = useRef(false);
  const { setLocale } = useLocale();

  // Set the user locale
  useEffect(() => {
    if (initDataUser && initDataRaw && !initAttempted.current) {
      if (initDataUser.languageCode) {
        setLocale(initDataUser.languageCode);
      }
      
      // Mark as attempted
      initAttempted.current = true;
      setIsInitialized(true);
    } else if (initDataUser && !initDataRaw) {
      // If we have user data but no raw init data, proceed anyway
      if (initDataUser.languageCode) {
        setLocale(initDataUser.languageCode);
      }
      setIsInitialized(true);
    }
  }, [initDataUser, initDataRaw, setLocale]);


  return (
    <>
      <AppRoot
        appearance={isDark ? 'dark' : 'light'}
        platform={['macos', 'ios'].includes(lp.platform) ? 'ios' : 'base'}
      >
        {children}
      </AppRoot>
    </>
  );
}

export function Root(props: PropsWithChildren) {
  // Unfortunately, Telegram Mini Apps does not allow us to use all features of
  // the Server Side Rendering. That's why we are showing loader on the server
  // side.
  const didMount = useDidMount();

  return didMount ? (
    <ErrorBoundary fallback={ErrorPage}>
      <RootInner {...props}/>
    </ErrorBoundary>
  ) : (
    <div className="root__loading">
      <Preloader />
    </div>
  );
}