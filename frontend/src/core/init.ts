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
  // If already initialized, don't reinitialize
  if (initialized) {
    console.log('SDK already initialized, skipping...');
    return;
  }
  
  initialized = true;
  console.log('🔧 Starting SDK initialization...');
  
  // Set @telegram-apps/sdk-react debug mode.
  $debug.set(debug);

  try {
    // Check if we're in a proper Telegram environment or mocked environment
    const isTelegramApp = isTMA('simple') || (typeof window !== 'undefined' && window.sessionStorage?.getItem("env-mocked"));
    const isDevelopment = process.env.NODE_ENV === 'development';
    
    console.log('🔍 SDK Init - Environment check:', {
      isTelegramApp,
      isDevelopment,
      hasWindow: typeof window !== 'undefined',
      sessionMocked: typeof window !== 'undefined' ? window.sessionStorage?.getItem("env-mocked") : null,
      isTMACheck: isTMA('simple')
    });
    
    if (!isTelegramApp && process.env.NODE_ENV === 'production') {
      console.warn('⚠️ Production app running outside Telegram environment');
    }
    
    // In development, ensure we have window.Telegram object before proceeding
    if (isDevelopment && typeof window !== 'undefined') {
      console.log('🔍 Checking window.Telegram object state:', {
        hasTelegram: !!window.Telegram,
        hasWebApp: !!(window.Telegram?.WebApp),
        webAppVersion: window.Telegram?.WebApp?.version
      });
    }
    
    // Initialize special event handlers for Telegram Desktop, Android, iOS, etc.
    // Also, configure the package.
    console.log('🚀 Calling initSDK...');
    initSDK();

    // Mount all components used in the project.
    console.log('🔧 Mounting SDK components...');
    
    if (backButton.isSupported() && !backButton.isMounted()) {
      console.log('📱 Mounting back button...');
      backButton.mount();
    }

    console.log('📊 Restoring init data...');
    initData.restore();

    if (!miniApp.isMounted()) {
      console.log('📱 Mounting mini app...');
      miniApp.mount();
    }

    if (!themeParams.isMounted()) {
      console.log('🎨 Mounting theme params...');
      themeParams.mount();
    }

    // Only attempt to mount viewport if it's not already mounted or mounting
    if (!viewport.isMounted() && !viewport.isMounting()) {
      console.log('📱 Mounting viewport...');
      void viewport.mount().catch((e) => {
        console.error("❌ Error mounting viewport:", e);
      });
    }

    // Define components-related CSS variables only once
    if (!cssVarsInitialized) {
      console.log('🎨 Binding CSS variables...');
      try {
        // Bind CSS variables
        miniApp.bindCssVars();
        
        if (viewport.isMounted()) {
          viewport.bindCssVars();
        }
        
        themeParams.bindCssVars();
        
        // Mark as initialized
        cssVarsInitialized = true;
        console.log('✅ CSS variables bound successfully');
      } catch (error) {
        console.warn("⚠️ Error binding CSS variables:", error);
        // Even if there's an error, mark as initialized to avoid repeated attempts
        cssVarsInitialized = true;
      }
    }

    // Add Eruda if needed.
    if (debug) {
      console.log('🐛 Loading Eruda for debugging...');
      import("eruda").then((lib) => lib.default.init()).catch(console.error);
    }
    
    // Mark SDK as ready for components to use
    sdkReady = true;
    console.log('✅ SDK marked as ready');
    
    // Let the app know the SDK is ready
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('telegram-sdk-ready'));
      console.log('📡 Dispatched telegram-sdk-ready event');
    }
    
    console.log('🎉 SDK initialization completed successfully!');
  } catch (error: any) {
    console.error("❌ Error initializing Telegram SDK:", error);
    
    // Handle specific ERR_UNKNOWN_ENV error with more detailed logging
    if (error.message?.includes('ERR_UNKNOWN_ENV') || error.toString?.().includes('ERR_UNKNOWN_ENV')) {
      console.warn("🔧 SDK initialization failed due to ERR_UNKNOWN_ENV");
      console.log("🔍 This typically means the mock environment wasn't properly set up or the SDK couldn't detect a valid Telegram environment");
      
      // Log current environment state for debugging
      if (typeof window !== 'undefined') {
        console.log("🔍 Current environment state:", {
          hasWindow: true,
          hasTelegram: !!window.Telegram,
          hasWebApp: !!(window.Telegram?.WebApp),
          sessionMocked: window.sessionStorage?.getItem("env-mocked"),
          isDevelopment: process.env.NODE_ENV === 'development'
        });
      }
      
      // In development, this error is expected if mock setup failed
      if (process.env.NODE_ENV === 'development') {
        console.warn("⚠️ Development mode: ERR_UNKNOWN_ENV suggests mock environment setup may have failed");
        console.warn("⚠️ Check the mockTelegramEnv.ts initialization in the browser console");
      }
    }
    
    // Even on error, mark as initialized to prevent retry loops
    // The app should still render with limited functionality
    sdkReady = true;
    console.log("✅ SDK marked as ready despite initialization error (app will continue with limited functionality)");
  }
}