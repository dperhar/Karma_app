import {
  $debug,
  backButton,
  initData,
  init as initSDK,
  miniApp,
  themeParams,
  viewport,
  isTMA,
} from "@telegram-apps/sdk-react";

// Track initialization state globally
let initialized = false;
let cssVarsInitialized = false;
export let sdkReady = false;

export function init(debug: boolean): void {
  // If already initialized with same debug value, don't reinitialize
  if (initialized) {
    return;
  }
  
  initialized = true;
  
  // Set @telegram-apps/sdk-react debug mode.
  $debug.set(debug);

  try {
    // Check if we're in a proper Telegram environment or mocked environment
    const isTelegramApp = isTMA('simple') || (typeof window !== 'undefined' && window.sessionStorage?.getItem("env-mocked"));
    
    console.log('Initializing SDK - Telegram environment:', isTelegramApp);
    
    // Initialize special event handlers for Telegram Desktop, Android, iOS, etc.
    // Also, configure the package.
    initSDK();

    // Mount all components used in the project.
    if (backButton.isSupported() && !backButton.isMounted()) {
      backButton.mount();
    }

    initData.restore();

    if (!miniApp.isMounted()) {
      miniApp.mount();
    }

    if (!themeParams.isMounted()) {
      themeParams.mount();
    }

    // Only attempt to mount viewport if it's not already mounted or mounting
    if (!viewport.isMounted() && !viewport.isMounting()) {
      void viewport.mount().catch((e) => {
        console.error("Something went wrong mounting the viewport", e);
      });
    }

    // Define components-related CSS variables only once
    if (!cssVarsInitialized) {
      try {
        // Bind CSS variables
        miniApp.bindCssVars();
        
        if (viewport.isMounted()) {
          viewport.bindCssVars();
        }
        
        themeParams.bindCssVars();
        
        // Mark as initialized
        cssVarsInitialized = true;
      } catch (error) {
        console.warn("Error binding CSS variables:", error);
        // Even if there's an error, mark as initialized to avoid repeated attempts
        cssVarsInitialized = true;
      }
    }

    // Add Eruda if needed.
    if (debug) {
      import("eruda").then((lib) => lib.default.init()).catch(console.error);
    }
    
    // Mark SDK as ready for components to use
    sdkReady = true;
    
    // Let the app know the SDK is ready
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('telegram-sdk-ready'));
    }
  } catch (error: any) {
    console.error("Error initializing Telegram SDK:", error);
    
    // Handle specific ERR_UNKNOWN_ENV error
    if (error.message?.includes('ERR_UNKNOWN_ENV') || error.toString?.().includes('ERR_UNKNOWN_ENV')) {
      console.warn("SDK initialization failed due to unknown environment. This is expected in localhost development.");
      // Try to initialize minimal mock environment
      try {
        if (typeof window !== 'undefined' && !window.sessionStorage?.getItem("env-mocked")) {
          // Force mock environment if not already set
          window.sessionStorage?.setItem("env-mocked", "1");
          console.log("Forced mock environment activation");
        }
      } catch (mockError) {
        console.warn("Could not set mock environment:", mockError);
      }
    }
    
    // Even on error, mark as initialized to prevent retry loops
    sdkReady = true;
  }
}