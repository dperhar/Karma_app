'use client';

import { Root } from '@/components/Root/Root';
import { I18nProvider } from '@/core/i18n/provider';
import type { Locale } from '@/core/i18n/types';
import { StoreInitializer } from './StoreInitializer';

// Import and trigger pre-initialization immediately
import '@/utils/preInitialize';

interface ProvidersProps {
  children: React.ReactNode;
  locale: Locale;
  messages: any;
}

export const Providers = ({ children, locale, messages }: ProvidersProps) => {
  return (
    <I18nProvider messages={messages} locale={locale}>
      <StoreInitializer>
        <Root>{children}</Root>
      </StoreInitializer>
    </I18nProvider>
  );
}; 