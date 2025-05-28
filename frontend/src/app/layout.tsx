import { Providers } from '@/components/Providers';
import type { Locale } from '@/core/i18n/types';
import type { Metadata } from 'next';
import { getLocale, getMessages } from 'next-intl/server';
import 'normalize.css/normalize.css';
import './_assets/globals.css';

export const metadata: Metadata = {
  title: 'DoubleKiss',
  description: 'DoubleKiss - Pool Game App',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const locale = (await getLocale()) as Locale;
  const messages = await getMessages();

  return (
    <html lang={locale} data-theme="dark">
      <body className="min-h-screen bg-base-200">
        <Providers locale={locale} messages={messages}>
          {children}
        </Providers>
      </body>
    </html>
  );
}
