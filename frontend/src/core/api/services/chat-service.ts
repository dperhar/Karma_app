import { APIResponse } from '@/types/api';
import { ChatListResponse, ChatMessagesResponse, TelegramChat } from '@/types/chat';
import { ApiClient } from '../api-client';

export class ChatService extends ApiClient {
  private readonly endpoint = '/telegram/chats';
  private readonly chatEndpoint = '/telegram/chat';

  constructor() {
    super();
    console.log('ChatService initialized with endpoint:', this.endpoint);
  }

  async getChats(initDataRaw?: string, limit: number = 50, offset: number = 0): Promise<APIResponse<ChatListResponse>> {
    console.log('getChats called with limit:', limit, 'offset:', offset);
    try {
      const response = await this.request<APIResponse<ChatListResponse>>(
        `${this.endpoint}/list?limit=${limit}&offset=${offset}`,
        {
          method: 'GET',
        },
        initDataRaw
      );
      
      console.log('getChats response:', response);
      return response;
    } catch (error) {
      console.error('Failed to fetch chats:', error);
      throw error;
    }
  }

  async getChat(chatId: string, initDataRaw?: string): Promise<APIResponse<TelegramChat>> {
    console.log('getChat called for chat ID:', chatId);
    try {
      const response = await this.request<APIResponse<TelegramChat>>(
        `${this.endpoint}/${chatId}`,
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
      
      console.log('getChat response:', response);
      return response;
    } catch (error) {
      console.error('Failed to fetch chat:', error);
      throw error;
    }
  }

  async getChatMessages(
    telegramId: number, 
    initDataRaw?: string, 
    limit: number = 10, 
    offset: number = 0
  ): Promise<APIResponse<ChatMessagesResponse>> {
    console.log(`getChatMessages called for chat telegram_id: ${telegramId}, limit: ${limit}, offset: ${offset}`);
    try {
      const response = await this.request<APIResponse<ChatMessagesResponse>>(
        `${this.chatEndpoint}/${telegramId}/messages?limit=${limit}&offset=${offset}`,
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
      
      console.log('getChatMessages response:', response);
      return response;
    } catch (error) {
      console.error(`Failed to fetch messages for chat ${telegramId}:`, error);
      throw error;
    }
  }
}

export const chatService = new ChatService(); 