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
      console.log('[ChatStore] fetchChats called with:', { initDataRaw: initDataRaw?.substring(0, 50) + '...', limit, offset });
      set({ isLoading: true, error: null });
      
      const response = await chatService.getChats(initDataRaw, limit, offset);
      console.log('[ChatStore] fetchChats raw response:', response);
      
      if (response.success && response.data) {
        console.log('[ChatStore] fetchChats success - data.chats:', response.data.chats);
        console.log('[ChatStore] fetchChats success - chats count:', response.data.chats?.length || 0);
        if (response.data.chats && response.data.chats.length > 0) {
          console.log('[ChatStore] fetchChats success - first few chats:', response.data.chats.slice(0, 3));
        }
        set({ chats: response.data.chats, isLoading: false });
      } else {
        console.error('[ChatStore] fetchChats failed:', response.message);
        set({ 
          error: response.message || 'Failed to fetch chats',
          isLoading: false
        });
      }
    } catch (error) {
      console.error('[ChatStore] Error in fetchChats:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred',
        isLoading: false
      });
    } finally {
      console.log('[ChatStore] fetchChats completed');
    }
  },

  fetchChat: async (chatId: string, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      console.log('[ChatStore] fetchChat called with chatId:', chatId);
      const response = await chatService.getChat(chatId, initDataRaw);
      
      if (response.success && response.data) {
        console.log('[ChatStore] fetchChat success:', response.data);
        set({ chat: response.data, isLoading: false });
      } else {
        console.error('[ChatStore] fetchChat failed:', response.message);
        set({ 
          error: response.message || 'Failed to fetch chat', 
          isLoading: false 
        });
      }
    } catch (error) {
      console.error('[ChatStore] Error in fetchChat:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
    }
  },
  
  reset: () => {
    console.log('[ChatStore] reset called');
    set({ chats: [], chat: null, isLoading: false, error: null });
  }
})); 