import {
  AIDialogCreate,
  AIDialogResponse,
  AIDialogWithMessages,
  AIRequestResponse,
  LangChainMessageRequest
} from '@/types/ai';
import { APIResponse } from '@/types/api';
import { ApiClient } from '../api-client';

export class AIDialogService extends ApiClient {
  private readonly endpoint = '/ai-dialogs';

  constructor() {
    super();
    console.log('AIDialogService initialized with endpoint:', this.endpoint);
  }

  async createDialog(dialogData: AIDialogCreate, initDataRaw?: string): Promise<APIResponse<AIDialogResponse>> {
    console.log('createDialog called with data:', dialogData);
    try {
      const response = await this.request<APIResponse<AIDialogResponse>>(
        `${this.endpoint}`,
        {
          method: 'POST',
          body: JSON.stringify(dialogData),
          headers: {
            'Content-Type': 'application/json'
          }
        },
        initDataRaw
      );
      
      console.log('createDialog response:', response);
      return response;
    } catch (error) {
      console.error('Failed to create dialog:', error);
      throw error;
    }
  }

  async getDialogsByChat(chatId: string, initDataRaw?: string): Promise<APIResponse<AIDialogResponse[]>> {
    console.log('getDialogsByChat called for chat ID:', chatId);
    try {
      const response = await this.request<APIResponse<AIDialogResponse[]>>(
        `${this.endpoint}/chat/${chatId}`,
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
      
      console.log('getDialogsByChat response:', response);
      return response;
    } catch (error) {
      console.error('Failed to fetch dialogs for chat:', error);
      throw error;
    }
  }

  async getDialogWithMessages(dialogId: string, initDataRaw?: string): Promise<APIResponse<AIDialogWithMessages>> {
    console.log('getDialogWithMessages called for dialog ID:', dialogId);
    try {
      const response = await this.request<APIResponse<AIDialogWithMessages>>(
        `${this.endpoint}/${dialogId}`,
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
      
      console.log('getDialogWithMessages response:', response);
      return response;
    } catch (error) {
      console.error('Failed to fetch dialog with messages:', error);
      throw error;
    }
  }

  async processMessage(messageRequest: LangChainMessageRequest, initDataRaw?: string): Promise<APIResponse<AIRequestResponse>> {
    console.log('processMessage called with request:', messageRequest);
    try {
      const response = await this.request<APIResponse<AIRequestResponse>>(
        `${this.endpoint}/message`,
        {
          method: 'POST',
          body: JSON.stringify(messageRequest),
          headers: {
            'Content-Type': 'application/json'
          }
        },
        initDataRaw
      );
      
      console.log('processMessage response:', response);
      return response;
    } catch (error) {
      console.error('Failed to process message:', error);
      throw error;
    }
  }
}

export const aiDialogService = new AIDialogService(); 