import { create } from 'zustand';

import { aiDialogService } from '@/core/api/services/ai-dialog-service';
import {
  AIDialogCreate,
  AIDialogMessageResponse,
  AIDialogResponse,
  AIDialogWithMessages,
  AIRequestResponse,
  LangChainMessageRequest
} from '@/types/ai';

interface AIDialogState {
  dialogs: AIDialogResponse[];
  currentDialog: AIDialogWithMessages | null;
  isLoading: boolean;
  error: string | null;
  
  // Fetch dialogs for a specific chat
  fetchDialogsByChat: (chatId: string, initDataRaw?: string) => Promise<void>;
  
  // Fetch a specific dialog with messages
  fetchDialogWithMessages: (dialogId: string, initDataRaw?: string) => Promise<void>;
  
  // Create a new dialog
  createDialog: (dialogData: AIDialogCreate, initDataRaw?: string) => Promise<AIDialogResponse | null>;
  
  // Send a message and get a response
  sendMessage: (messageRequest: LangChainMessageRequest, initDataRaw?: string) => Promise<AIRequestResponse | null>;
  
  // Reset the current state
  reset: () => void;
}

export const useAIDialogStore = create<AIDialogState>((set, get) => ({
  dialogs: [],
  currentDialog: null,
  isLoading: false,
  error: null,
  
  fetchDialogsByChat: async (chatId: string, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await aiDialogService.getDialogsByChat(chatId, initDataRaw);
      
      if (response.success && response.data) {
        set({ dialogs: response.data, isLoading: false });
      } else {
        set({ 
          error: response.message || 'Failed to fetch dialogs', 
          isLoading: false 
        });
      }
    } catch (error) {
      console.error('Error in fetchDialogsByChat:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
    }
  },
  
  fetchDialogWithMessages: async (dialogId: string, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await aiDialogService.getDialogWithMessages(dialogId, initDataRaw);
      
      if (response.success && response.data) {
        console.log('Raw dialog with messages from API:', response.data);
        
        // Преобразуем сообщения из нового формата API в формат AIDialogMessageResponse
        const transformedMessages = response.data.messages.map(msg => {
          // Проверяем, что сообщения в новом формате API (имеют поля request_text и response_text)
          if ('request_text' in msg && 'response_text' in msg) {
            // Создаем пользовательское сообщение (запрос)
            const userMessage: AIDialogMessageResponse = {
              id: msg.id + '_user',
              dialog_id: msg.dialog_id,
              content: String(msg.request_text || ''),
              role: 'user',
              created_at: msg.created_at,
              updated_at: msg.updated_at
            };
            
            // Создаем сообщение ассистента (ответ)
            const assistantMessage: AIDialogMessageResponse = {
              id: msg.id,
              dialog_id: msg.dialog_id,
              content: String(msg.response_text || ''),
              role: 'assistant',
              model: msg.model,
              created_at: msg.created_at,
              updated_at: msg.updated_at
            };
            
            // Возвращаем массив из двух сообщений
            return [userMessage, assistantMessage];
          } else {
            // Если сообщение в старом формате, возвращаем как есть
            return [msg as AIDialogMessageResponse];
          }
        });
        
        // Преобразуем массив массивов сообщений в плоский массив
        const flattenedMessages = transformedMessages.flat();
        
        // Сортируем сообщения по времени создания
        flattenedMessages.sort((a, b) => 
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
        
        console.log('Transformed messages for UI:', flattenedMessages);
        
        set({ 
          currentDialog: { 
            dialog: response.data.dialog,
            messages: flattenedMessages
          }, 
          isLoading: false 
        });
      } else {
        set({ 
          error: response.message || 'Failed to fetch dialog with messages', 
          isLoading: false 
        });
      }
    } catch (error) {
      console.error('Error in fetchDialogWithMessages:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
    }
  },
  
  createDialog: async (dialogData: AIDialogCreate, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await aiDialogService.createDialog(dialogData, initDataRaw);
      
      if (response.success && response.data) {
        // Add the new dialog to the list of dialogs
        set((state) => {
          const nextDialogs: AIDialogResponse[] = [...state.dialogs];
          if (response.data) {
            nextDialogs.push(response.data as AIDialogResponse);
          }
          return {
            dialogs: nextDialogs,
            isLoading: false,
          };
        });
        return response.data;
      } else {
        set({ 
          error: response.message || 'Failed to create dialog', 
          isLoading: false 
        });
        return null;
      }
    } catch (error) {
      console.error('Error in createDialog:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
      return null;
    }
  },
  
  sendMessage: async (messageRequest: LangChainMessageRequest, initDataRaw?: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await aiDialogService.processMessage(messageRequest, initDataRaw);
      
      if (response.success && response.data) {
        // Update the current dialog with the new message if we're viewing it
        const currentDialog = get().currentDialog;
        if (currentDialog && currentDialog.dialog.id === messageRequest.dialog_id) {
          await get().fetchDialogWithMessages(messageRequest.dialog_id, initDataRaw);
        }
        
        set({ isLoading: false });
        return response.data;
      } else {
        set({ 
          error: response.message || 'Failed to process message', 
          isLoading: false 
        });
        return null;
      }
    } catch (error) {
      console.error('Error in sendMessage:', error);
      set({ 
        error: error instanceof Error ? error.message : 'An unknown error occurred', 
        isLoading: false 
      });
      return null;
    }
  },
  
  reset: () => {
    set({ 
      dialogs: [],
      currentDialog: null,
      isLoading: false,
      error: null 
    });
  }
})); 