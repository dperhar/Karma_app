import { chatService } from '@/core/api/services/chat-service';
import { TelegramChat } from '@/types/chat';
import { create } from 'zustand';

interface ChatState {
  chats: TelegramChat[];
  chat: TelegramChat | null;
  isLoading: boolean;
  error: string | null;
  
  fetchChats: (initDataRaw?: string, limit?: number, offset?: number) => Promise<void>;
  fetchChat: (chatId: string, initDataRaw?: string) => Promise<void>;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  chats: [],
  chat: null,
  isLoading: false,
  error: null,
  
  fetchChats: async (initDataRaw?: string, limit: number = 50, offset: number = 0) => {
    try {
      set({ isLoading: true, error: null });
      const response = await chatService.getChats(initDataRaw, limit, offset);
      
      if (response.success && response.data) {
        set({ chats: response.data.chats, isLoading: false });
      } else {
        set({ 
          error: response.message || 'Failed to fetch chats',
          isLoading: false
        });
      }
    } catch (error) {
      console.error('Error in fetchChats:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred',
        isLoading: false
      });
    }
  },

  fetchChat: async (chatId: string, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await chatService.getChat(chatId, initDataRaw);
      
      if (response.success && response.data) {
        set({ chat: response.data, isLoading: false });
      } else {
        set({ 
          error: response.message || 'Failed to fetch chat', 
          isLoading: false 
        });
      }
    } catch (error) {
      console.error('Error in fetchChat:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
    }
  },
  
  reset: () => {
    set({ chats: [], chat: null, isLoading: false, error: null });
  }
})); 