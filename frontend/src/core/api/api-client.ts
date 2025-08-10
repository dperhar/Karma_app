export class ApiClient {
  private readonly baseUrl: string;
  private readonly MAX_REDIRECTS: number = 3;
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
    initDataRaw?: string,
    redirectCount: number = 0
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
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120 секунд таймаут для телеграм API
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        ...options,
        // Ensure cookies (session) are sent to the API
        credentials: 'include',
        headers,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        // Обрабатываем 401 ошибку аутентификации
        if (response.status === 401) {
          console.log(`Authentication failed for ${endpoint}. Redirect count: ${redirectCount}`);
          
          // Предотвращаем бесконечные редиректы
          if (redirectCount >= this.MAX_REDIRECTS) {
            console.error(`Maximum redirect count (${this.MAX_REDIRECTS}) reached for ${endpoint}`);
            throw new Error(`Authentication error: Maximum redirect count reached for ${endpoint}`);
          }
          
          // Просто бросаем ошибку аутентификации без редиректа
          throw new Error('Authentication required');
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
        throw new Error('Network error: Failed to fetch');
      }
      
      throw error;
    }
  }
} 