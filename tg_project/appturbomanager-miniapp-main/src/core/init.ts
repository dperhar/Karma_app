import {
  $debug,
  backButton,
  initData,
  init as initSDK,
  miniApp,
  themeParams,
  viewport,
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
  } catch (error) {
    console.error("Error initializing Telegram SDK:", error);
    // Even on error, mark as initialized to prevent retry loops
    sdkReady = true;
  }
}