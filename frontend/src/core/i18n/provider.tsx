'use client';

import { NextIntlClientProvider } from "next-intl";
import React from "react";

import { timeZone } from "./config";
import type { Locale } from "./types";

const I18nProvider = ({
  messages,
  children,
  locale,
}: {
  messages: any;
  children: React.ReactNode;
  locale: Locale;
}) => {
  return (
    <NextIntlClientProvider messages={messages} timeZone={timeZone} locale={locale}>
      {children}
    </NextIntlClientProvider>
  );
};

export { I18nProvider };
