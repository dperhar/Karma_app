export class ApiClient {
  private readonly baseUrl: string;
  private redirectCount: number = 0;
  private readonly MAX_REDIRECTS: number = 1;
  private readonly isDev: boolean;

  constructor(baseUrl: string = process.env.NEXT_PUBLIC_API_URL || '') {
    if (!baseUrl) {
      throw new Error('API base URL is not configured. Please set NEXT_PUBLIC_API_URL environment variable.');
    }
    this.baseUrl = baseUrl;
    this.isDev = process.env.NODE_ENV === 'development';
    console.log('ApiClient initialized with baseUrl:', this.baseUrl);
    console.log('Environment:', this.isDev ? 'development' : 'production');
  }

  protected async request<T>(
    endpoint: string,
    options: RequestInit = {},
    initDataRaw?: string
  ): Promise<T> {
    console.log(`ApiClient request called with endpoint: ${endpoint}`);
    console.log('Request options:', {
      method: options.method,
      headers: options.headers,
      body: options.body
    });
    console.log('Full URL will be:', `${this.baseUrl}${endpoint}`);
    
    const headers: Record<string, string> = {
      ...(!(options.body instanceof FormData) && { 'Content-Type': 'application/json' }),
      ...(options.headers as Record<string, string> || {}),
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Telegram-Init-Data'
    };

    // Validate initDataRaw
    if (!initDataRaw) {
      console.warn('initDataRaw is missing. Authentication may fail.');
      
      if (!this.isDev) {
        throw new Error('Telegram init data is required for authentication');
      } else {
        console.log('Running in development mode, continuing without init data');
      }
    }

    // Add initDataRaw to headers if available
    if (initDataRaw) {
      headers['X-Telegram-Init-Data'] = initDataRaw;
    }

    // Добавляем кеш-контроль для предотвращения проблем с кешированием ответов
    headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
    headers['Pragma'] = 'no-cache';
    headers['Expires'] = '0';

    try {
      // Добавляем таймаут для предотвращения зависания запросов
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 секунд таймаут
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        headers,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        // Обрабатываем 401 ошибку аутентификации
        if (response.status === 401 && typeof window !== 'undefined') {
          // Предотвращаем бесконечные редиректы
          if (this.redirectCount < this.MAX_REDIRECTS) {
            this.redirectCount++;
            console.log('Authentication error, redirecting to registration page');
            return {} as T;
          } else {
            console.error('Maximum redirect count reached');
            throw new Error('Authentication error: Maximum redirect count reached');
          }
        }

        let errorMessage: string;
        try {
          const errorData = await response.json();
          errorMessage = errorData.message || errorData.error || JSON.stringify(errorData);
        } catch {
          errorMessage = await response.text();
        }
        throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorMessage}`);
      }

      // Сбрасываем счетчик редиректов при успешном запросе
      this.redirectCount = 0;

      // Пытаемся прочитать ответ как JSON
      try {
        const data = await response.json();
        return data;
      } catch {
        // Если не получилось прочитать как JSON, возвращаем как текст
        const text = await response.text();
        return text as unknown as T;
      }
    } catch (error) {
      console.error('API request error:', error);
      
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw new Error('Request timeout: The server took too long to respond');
      }
      
      if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
        console.log('Network error detected');
        
        // Предотвращаем бесконечные редиректы
        if (typeof window !== 'undefined' && this.redirectCount < this.MAX_REDIRECTS) {
          this.redirectCount++;
          
          // Проверяем, не находимся ли мы уже на странице регистрации
          if (!window.location.pathname.includes('registration-required')) {
            console.log('Redirecting to registration page');
            // Используем мягкий редирект вместо window.location.href
            // window.history.pushState({}, '', '/registration-required');
            return {} as T;
          }
        }
      }
      
      throw error;
    }
  }
} 