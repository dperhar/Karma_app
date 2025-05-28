import { getLocale, getMessages } from "next-intl/server";
import React from "react";

import { I18nProvider } from "./provider";
import type { Locale } from "./types";

const MessagesProvider = async ({
  children,
}: {
  children: React.ReactNode;
}) => {
  const messages = await getMessages();
  const locale = (await getLocale()) as Locale;
  
  return <I18nProvider messages={messages} locale={locale}>{children}</I18nProvider>;
};

export { MessagesProvider };
