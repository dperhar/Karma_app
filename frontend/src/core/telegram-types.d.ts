interface TelegramWebApp {
  WebApp: any; // You can expand this type based on the actual WebApp properties you need
}

declare interface Window {
  Telegram?: TelegramWebApp;
} 