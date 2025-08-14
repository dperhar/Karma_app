import { APIResponse } from '@/types/api';
import { User, UserUpdate } from '@/types/user';
import { ApiClient } from '../api-client';

// Add interface for context analysis response
interface UserContextAnalysisResult {
  status: string;
  style_analysis?: any;
  interests_analysis?: any;
  style_description?: string;
  system_prompt?: string;
  reason?: string;
}

export class UserService extends ApiClient {
  private readonly endpoint = '/users';
  private readonly aiProfileEndpoint = '/users/me/ai-profile';

  constructor() {
    super();
    console.log('UserService initialized with endpoint:', this.endpoint);
  }

  async getCurrentUser(initDataRaw?: string): Promise<APIResponse<User>> {
    console.log('getCurrentUser called');
    try {
      // Add timestamp to prevent caching - only on client side
      const timestampParam = typeof window !== 'undefined' ? `?_t=${new Date().getTime()}` : '';
      const response = await this.request<APIResponse<User>>(
        `${this.endpoint}/me${timestampParam}`,
        {
          method: 'GET',
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
          }
        },
        initDataRaw
      );
      
      console.log('getCurrentUser response:', response);
      return response;
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      throw error;
    }
  }

  async getMyAIProfile(initDataRaw?: string) {
    try {
      const response = await this.request<APIResponse<any>>(this.aiProfileEndpoint, { method: 'GET' }, initDataRaw);
      return response;
    } catch (error) {
      console.error('Failed to fetch AI profile:', error);
      throw error;
    }
  }

  async updateMyAIProfile(body: any, initDataRaw?: string) {
    return this.request<APIResponse<any>>(
      `${this.aiProfileEndpoint}`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      },
      initDataRaw
    );
  }

  async updateUser(userData: UserUpdate, initDataRaw?: string): Promise<APIResponse<User>> {
    console.log('updateUser called with data:', userData);
    console.log('Using initDataRaw:', initDataRaw ? 'provided' : 'not provided');
    try {
      const response = await this.request<APIResponse<User>>(
        `${this.endpoint}/me`,
        {
          method: 'PUT',
          body: JSON.stringify(userData),
          headers: {
            'Content-Type': 'application/json'
          }
        },
        initDataRaw
      );
      
      console.log('updateUser response:', response);
      return response;
    } catch (error) {
      console.error('Failed to update user:', error);
      throw error;
    }
  }

  async analyzeUserContext(initDataRaw?: string): Promise<APIResponse<UserContextAnalysisResult>> {
    console.log('analyzeUserContext called');
    try {
      const response = await this.request<APIResponse<UserContextAnalysisResult>>(
        `${this.endpoint}/me/analyze-context`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        },
        initDataRaw
      );
      
      console.log('analyzeUserContext response:', response);
      return response;
    } catch (error) {
      console.error('Failed to analyze user context:', error);
      throw error;
    }
  }

  async getAISettings(initDataRaw?: string) {
    return this.request<APIResponse<any>>(`/users/me/ai-settings`, { method: 'GET' }, initDataRaw);
  }

  async updateAISettings(body: { model?: string; temperature?: number; max_output_tokens?: number }, initDataRaw?: string) {
    return this.request<APIResponse<any>>(
      `/users/me/ai-settings`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      initDataRaw
    );
  }

  async subPersonaClassifyPreview(postText: string, initDataRaw?: string) {
    return this.request<APIResponse<{ persona: string | null; score: number; breakdown: { semantic: number; keywords: number } }>>(
      `/users/me/subpersona-classify-preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_text: postText }),
      },
      initDataRaw
    );
  }

  // --- Digital Twin Freeform compiler endpoints ---
  async dtFreeformPreview(content: string, initDataRaw?: string) {
    return this.request<APIResponse<any>>(
      `/users/me/dt-config/freeform/preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      },
      initDataRaw
    );
  }

  async dtFreeformApply(
    body: { content: string; apply_mask: Record<string, boolean>; strategy: 'merge' | 'replace' },
    initDataRaw?: string
  ) {
    return this.request<APIResponse<any>>(
      `/users/me/dt-config/freeform/apply`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      },
      initDataRaw
    );
  }

  async dtFreeformLast(initDataRaw?: string) {
    return this.request<APIResponse<{ dt_freeform: any; dt_config: any }>>(
      `/users/me/dt-config/freeform/last`,
      { method: 'GET' },
      initDataRaw
    );
  }

  async dtFreeformSeedFromProfile(initDataRaw?: string) {
    return this.request<APIResponse<{ freeform: string; last_analyzed_at?: string; tokens_estimate?: number; source: string }>>(
      `/users/me/dt-config/freeform/seed-from-profile`,
      { method: 'GET' },
      initDataRaw
    );
  }

  async dtFreeformSeedFromCache(initDataRaw?: string) {
    return this.request<APIResponse<{ status: string }>>(
      `/users/me/dt-config/freeform/seed-from-cache`,
      { method: 'POST' },
      initDataRaw
    );
  }

  async dtFreeformRollback(versionId: string, initDataRaw?: string) {
    return this.request<APIResponse<any>>(
      `/users/me/dt-config/rollback`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_id: versionId }),
      },
      initDataRaw
    );
  }

  async previewComment(postText: string, initDataRaw?: string) {
    return this.request<APIResponse<{ status: string }>>(
      `/users/me/preview-comment`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ post_text: postText }),
      },
      initDataRaw
    );
  }

}

export const userService = new UserService(); 