export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  status_code?: number;
}

export interface ErrorResponse {
  success: false;
  message: string;
  status_code?: number;
} 