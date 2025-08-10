'use client';

import { Root } from '@/components/Root/Root';
import { I18nProvider } from '@/core/i18n/provider';
import type { Locale } from '@/core/i18n/types';
import { StoreInitializer } from './StoreInitializer';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useCommentStore } from '@/store/commentStore';

// Import and trigger pre-initialization immediately
import '@/utils/preInitialize';

interface ProvidersProps {
  children: React.ReactNode;
  locale: Locale;
  messages: any;
}

export const Providers = ({ children, locale, messages }: ProvidersProps) => {
  const userId = (typeof window !== 'undefined' && sessionStorage.getItem('persistent-user-id')) || undefined;
  const { lastMessage } = useWebSocket({ userId });
  // Bridge WS messages into comment store
  React.useEffect(() => {
    if (!lastMessage) return;
    const { event, data } = lastMessage as any;
    if (event === 'new_ai_draft' || event === 'draft_update' || event === 'draft_regenerated') {
      try {
        const draft = data?.draft ?? data;
        if (!draft?.id) return;
        useCommentStore.setState((state) => ({
          drafts: state.drafts.some((d) => d.id === draft.id)
            ? state.drafts.map((d) => (d.id === draft.id ? { ...d, ...draft } : d))
            : [...state.drafts, draft],
        }));
      } catch (e) {
        console.error('WS apply error', e);
      }
    }
  }, [lastMessage]);
  return (
    <I18nProvider messages={messages} locale={locale}>
      <StoreInitializer>
        <Root>{children}</Root>
      </StoreInitializer>
    </I18nProvider>
  );
}; 