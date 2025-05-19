export interface APIResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
} 