import { APIResponse } from '@/types/api';
import { ApiClient } from '../api-client';

interface QRCodeResponse {
  token: string;
}

interface LoginCheckResponse {
  requires_2fa: boolean;
  user_id: number | null;
  status: string | null;
}

interface TwoFactorAuthRequest {
  password: string;
}

export class AuthService extends ApiClient {
  private readonly endpoint = '/telegram/auth';

  constructor() {
    super();
    console.log('AuthService initialized with endpoint:', this.endpoint);
  }

  async generateQRCode(initDataRaw?: string): Promise<APIResponse<QRCodeResponse>> {
    console.log('generateQRCode called');
    try {
      const response = await this.request<APIResponse<QRCodeResponse>>(
        `${this.endpoint}/qr-code`,
        {
          method: 'POST',
        },
        initDataRaw
      );
      
      console.log('generateQRCode response:', response);
      return response;
    } catch (error) {
      console.error('Failed to generate QR code:', error);
      throw error;
    }
  }

  async checkQRLogin(token: string, initDataRaw: string): Promise<APIResponse<LoginCheckResponse>> {
    console.log('checkQRLogin called for token:', token);
    try {
      const response = await this.request<APIResponse<LoginCheckResponse>>(
        `${this.endpoint}/check`,
        {
          method: 'POST',
          body: JSON.stringify({ token }),
          headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': initDataRaw
          }
        },
        initDataRaw
      );
      
      console.log('checkQRLogin response:', response);
      return response;
    } catch (error) {
      console.error('Failed to check QR login:', error);
      throw error;
    }
  }

  async verify2FA(token: string, initDataRaw: string, password: string): Promise<APIResponse<LoginCheckResponse>> {
    console.log('verify2FA called for token:', token);
    try {
      const response = await this.request<APIResponse<LoginCheckResponse>>(
        `${this.endpoint}/verify-2fa/${token}`,
        {
          method: 'POST',
          body: JSON.stringify({ password }),
          headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': initDataRaw
          }
        },
        initDataRaw
      );
      
      console.log('verify2FA response:', response);
      return response;
    } catch (error) {
      console.error('Failed to verify 2FA:', error);
      throw error;
    }
  }
}

export const authService = new AuthService(); 