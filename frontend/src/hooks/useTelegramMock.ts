import {
  isTMA,
  type LaunchParams,
  mockTelegramEnv,
  parseInitData,
  retrieveLaunchParams,
} from "@telegram-apps/sdk-react";

// Track if environment has been mocked
let envMockedGlobally = false;

/**
 * Mocks Telegram environment in development mode.
 */
export function useTelegramMock(): void {
  // Skip the client check - always initialize on both server and client
  // Since we're in a React hook context, this will be proper
  
  // Skip if already mocked globally or if real Telegram environment is detected
  if (envMockedGlobally || (typeof window !== 'undefined' && !sessionStorage.getItem("env-mocked") && isTMA("simple"))) {
    console.log('Telegram environment already mocked or real Telegram environment detected');
    return;
  }

  // Determine which launch params should be applied. We could already
  // apply them previously, or they may be specified on purpose using the
  // default launch parameters transmission method.
  let lp: LaunchParams | undefined;
  try {
    lp = retrieveLaunchParams();
    console.log('useTelegramMock.ts:31 Retrieved launch params:', lp);
  } catch (e) {
    console.log('Failed to retrieve launch params, applying mock data');
    const initDataRaw = new URLSearchParams([
      [
        "user",
        JSON.stringify({
          id: 118672216,
          first_name: "🔥A1🔥",
          last_name: "",
          username: "a1turbotop",
          language_code: "ru",
          is_premium: true,
          allows_write_to_pm: true,
        }),
      ],
      ["auth_date", "1735583847"],
      ["hash", "abcd1234"],
      ["start_param", "debug"],
      ["chat_type", "sender"],
      ["chat_instance", "-1000000000000000000"],
    ]).toString();

    console.log('useTelegramMock.ts:52 Created mock initDataRaw:', initDataRaw);

    lp = {
      themeParams: {
        accentTextColor: "#6ab2f2",
        bgColor: "#17212b",
        buttonColor: "#5288c1",
        buttonTextColor: "#ffffff",
        destructiveTextColor: "#ec3942",
        headerBgColor: "#17212b",
        hintColor: "#708499",
        linkColor: "#6ab3f3",
        secondaryBgColor: "#232e3c",
        sectionBgColor: "#17212b",
        sectionHeaderTextColor: "#6ab3f3",
        subtitleTextColor: "#708499",
        textColor: "#f5f5f5",
      },
      initData: parseInitData(initDataRaw),
      initDataRaw,
      version: "8",
      platform: "tdesktop",
    };
  }

  if (typeof window !== 'undefined') {
    sessionStorage.setItem("env-mocked", "1");
  }
  envMockedGlobally = true;
  mockTelegramEnv(lp);
  console.info("🔄 Environment was mocked by the mockTelegramEnv function");
  console.warn(
    "⚠️ As long as the current environment was not considered as the Telegram-based one, it was mocked. Take a note, that you should not do it in production and current behavior is only specific to the development process. Environment mocking is also applied only in development mode. So, after building the application, you will not see this behavior and related warning, leading to crashing the application outside Telegram.",
  );
}