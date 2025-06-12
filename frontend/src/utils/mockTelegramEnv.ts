import {
  type LaunchParams,
  mockTelegramEnv,
  parseInitData,
  retrieveLaunchParams,
  isTMA,
} from "@telegram-apps/sdk-react";

// Track if environment has been mocked globally
let envMockedGlobally = false;

/**
 * Synchronously mock Telegram environment for development.
 * This must be called BEFORE React starts rendering to avoid race conditions.
 */
export function initMockTelegramEnv(): void {
  // Only run in development and only once
  if (process.env.NODE_ENV !== 'development' || envMockedGlobally) {
    return;
  }

  // If already mocked via session storage, skip
  if (typeof window !== 'undefined' && window.sessionStorage.getItem("env-mocked")) {
    console.log('Environment already mocked, skipping re-initialization');
    envMockedGlobally = true;
    return;
  }

  // Force mock setup in development, regardless of what isTMA() returns
  // This ensures a consistent and predictable environment for development
  console.log('Development mode: Forcing Telegram mock environment setup');

  // Determine which launch params should be applied
  let lp: LaunchParams | undefined;
  try {
    lp = retrieveLaunchParams();
    console.log('mockTelegramEnv: Retrieved existing launch params:', lp);
  } catch (e) {
    console.log('Failed to retrieve launch params, creating mock data for development');
    
    // Create mock data compatible with Telethon user account
    const mockUser = {
      id: 118672216,
      first_name: "🔥A1🔥",
      last_name: "",
      username: "a1turbotop",
      language_code: "ru",
      is_premium: true,
      allows_write_to_pm: true,
    };

    // Create initDataRaw with hash for development (required by SDK)
    const authDate = Math.floor(Date.now() / 1000);
    const initDataRaw = new URLSearchParams([
      ["user", JSON.stringify(mockUser)],
      ["auth_date", authDate.toString()],
      [
        "signature",
        "SignaturePkdisAdGwQepp8pmdCeUM6k_NKjxU5aiofGrn_TelethonDevMock_UzResG0mLxuPcQZT5rlnWDw",
      ],
      [
        "hash",
        "89d6079ad6762351f38c6dbbc41bb53048019256a9443988af7a48bcad16ba31",
      ],
      ["start_param", "debug"],
      ["chat_type", "sender"],
      ["chat_instance", "-1000000000000000000"],
    ]).toString();

    console.log('mockTelegramEnv: Created mock initDataRaw for development:', initDataRaw);

    // Create minimal valid launch params for mocking
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
      startParam: "debug",
    };
  }

  // Set session storage flag first
  if (typeof window !== 'undefined') {
    sessionStorage.setItem("env-mocked", "1");
  }
  
  // Mock the environment with our Telethon-compatible setup
  if (lp) {
    try {
      mockTelegramEnv(lp);
      envMockedGlobally = true;
      console.info("🔄 Telegram environment mocked successfully for development");
    } catch (error) {
      console.warn("⚠️ Error mocking Telegram environment:", error);
      // Still mark as mocked to prevent retry loops
      envMockedGlobally = true;
    }
  } else {
    console.warn("⚠️ No launch params available for mocking");
    envMockedGlobally = true;
  }
  
  console.warn(
    "⚠️ Development mode: Telegram environment mocked. This should not be used in production.",
  );
}

/**
 * Check if the environment has been properly mocked
 */
export function isEnvironmentMocked(): boolean {
  return envMockedGlobally || (typeof window !== 'undefined' && sessionStorage.getItem("env-mocked") === "1");
} 