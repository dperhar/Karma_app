/**
 * Detects if the current device is a mobile device
 * @returns {boolean} true if the device is mobile, false otherwise
 */
export const isMobileDevice = (): boolean => {
  // Check if window is defined (to avoid SSR issues)
  if (typeof window === 'undefined') return false;
  
  // Regular expression to match common mobile user agent patterns
  const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i;
  
  return mobileRegex.test(navigator.userAgent) || 
         (window.innerWidth <= 768) || // Common mobile breakpoint
         (('ontouchstart' in window) && window.matchMedia('(max-width: 1024px)').matches);
};

/**
 * Checks if we're running inside a Telegram WebApp
 * @returns {boolean} true if running inside Telegram WebApp
 */
export const isTelegramWebApp = (): boolean => {
  return typeof window !== 'undefined' && 
         !!(window as any).Telegram?.WebApp;
};

/**
 * Opens a Telegram link with proper handling for desktop vs mobile
 * @param {string} username - The Telegram username to link to
 * @returns {void}
 */
export const openTelegramChat = (username: string): void => {
  if (!username) {
    console.error('Cannot open Telegram chat: No username provided');
    return;
  }

  const cleanUsername = username.toLowerCase().replace('@', '');
  const telegramUrl = `https://t.me/${cleanUsername}`;
  
  // Inside Telegram WebApp on Mobile
  if (isTelegramWebApp()) {
    try {
      console.log('Opening via WebApp: ', telegramUrl);
      (window as any).Telegram.WebApp.openTelegramLink(telegramUrl);
      return;
    } catch (e) {
      console.error('Error opening Telegram link via WebApp: ', e);
      // Fall through to other methods if this fails
    }
  }
  
  // Regular browser approach
  try {
    console.log('Opening via window.open: ', telegramUrl);
    window.open(telegramUrl, '_blank');
  } catch (e) {
    console.error('Error opening Telegram link in new tab: ', e);
    
    // Last resort: change location
    try {
      window.location.href = telegramUrl;
    } catch (e) {
      console.error('Failed to navigate to Telegram: ', e);
    }
  }
}; 