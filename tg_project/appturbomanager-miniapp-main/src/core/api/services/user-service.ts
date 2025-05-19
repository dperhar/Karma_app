import { APIResponse } from '@/types/api';
import { User, UserUpdate } from '@/types/user';
import { ApiClient } from '../api-client';


export class UserService extends ApiClient {
  private readonly endpoint = '/users';

  constructor() {
    super();
    console.log('UserService initialized with endpoint:', this.endpoint);
  }

  async getCurrentUser(initDataRaw?: string): Promise<APIResponse<User>> {
    console.log('getCurrentUser called');
    try {
      // Add timestamp to prevent caching
      const timestamp = new Date().getTime();
      const response = await this.request<APIResponse<User>>(
        `${this.endpoint}/me?_t=${timestamp}`,
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

}

export const userService = new UserService(); 