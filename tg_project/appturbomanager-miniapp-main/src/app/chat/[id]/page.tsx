'use client';

import { initData, useSignal } from '@telegram-apps/sdk-react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { AIDialogList } from '@/components/AIDialog/AIDialogList';
import { AIMessage } from '@/components/AIDialog/AIMessage';
import { MessageInput } from '@/components/AIDialog/MessageInput';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { chatService } from '@/core/api/services/chat-service';
import { useAIDialogStore } from '@/store/aiDialogStore';
import { useChatStore } from '@/store/chatStore';
import { useUserStore } from '@/store/userStore';
import { AIDialogResponse, LangChainMessageRequest } from '@/types/ai';
import { TelegramChat, TelegramMessage } from '@/types/chat';

// Default values if user preferences are not set
const DEFAULT_CONTEXT_SIZE = 10;
const DEFAULT_MODEL = "gpt-3.5-turbo";
const DEFAULT_MAX_TOKENS = 2000;
const DEFAULT_MESSAGES_LOAD_LIMIT = 20;

export default function ChatDetailPage() {
  const t = useTranslations('i18n');
  const router = useRouter();
  const { id: rawChatId } = useParams();
  const chatId = typeof rawChatId === 'string' ? rawChatId : '';
  
  // Get initialization data from Telegram
  const initDataRaw = useSignal(initData.raw);
  
  // State for the current chat and dialogs
  const [currentChat, setCurrentChat] = useState<TelegramChat | null>(null);
  const [selectedDialog, setSelectedDialog] = useState<AIDialogResponse | null>(null);
  const [isCreatingDialog, setIsCreatingDialog] = useState(false);
  const [chatMessages, setChatMessages] = useState<TelegramMessage[]>([]);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  
  // Get chat data from store
  const { fetchChat, chat: chatData, isLoading: chatLoading, error: chatError } = useChatStore();
  
  // Get AI dialog data from store
  const { 
    dialogs, 
    currentDialog,
    fetchDialogsByChat, 
    fetchDialogWithMessages,
    createDialog,
    sendMessage,
    isLoading: dialogsLoading, 
    error: dialogsError
  } = useAIDialogStore();

  // Get user data from store
  const { user } = useUserStore();
  
  // Fetch chat data and dialogs on initial load
  useEffect(() => {
    const loadData = async () => {
      if (!chatId || !initDataRaw) {
        return;
      }
      
      try {
        // Fetch chat data
        await fetchChat(chatId, initDataRaw);
      } catch (error) {
        console.error('Error loading chat data:', error);
      }
    };
    
    loadData();
    
    // Cleanup function
    return () => {
      // Reset AI dialog store when leaving the page
      useAIDialogStore.getState().reset();
    };
  }, [chatId, fetchChat, initDataRaw]);
  
  // When chat data is loaded, fetch the AI dialogs using the internal chat.id
  useEffect(() => {
    if (chatData && initDataRaw) {
      setCurrentChat(chatData);
      
      // Use the chat's actual id to fetch dialogs, not the telegram_id
      fetchDialogsByChat(chatData.id, initDataRaw);
      
      // Load chat messages using the telegram_id
      loadChatMessages(chatData.telegram_id);
    }
  }, [chatData, fetchDialogsByChat, initDataRaw]);
  
  // Load chat messages from the API
  const loadChatMessages = async (telegramId: number) => {
    if (!initDataRaw) return;
    
    try {
      setIsLoadingMessages(true);
      setMessagesError(null);
      
      // Get user's preferred message load limit or use default
      const messagesLimit = user?.telegram_messages_load_limit || DEFAULT_MESSAGES_LOAD_LIMIT;
      
      // Fetch messages from API
      const response = await chatService.getChatMessages(
        telegramId,
        initDataRaw,
        messagesLimit,
        0 // Start from the beginning
      );
      
      if (response.success && response.data) {
        setChatMessages(response.data.messages);
      } else {
        setMessagesError(response.message || 'Failed to load chat messages');
      }
    } catch (error) {
      console.error('Error loading chat messages:', error);
      setMessagesError('An error occurred while loading chat messages');
    } finally {
      setIsLoadingMessages(false);
    }
  };
  
  // Load selected dialog details when a dialog is selected
  useEffect(() => {
    if (selectedDialog && initDataRaw) {
      fetchDialogWithMessages(selectedDialog.id, initDataRaw);
    }
  }, [selectedDialog, fetchDialogWithMessages, initDataRaw]);
  
  // Handle dialog selection
  const handleDialogClick = (dialog: AIDialogResponse) => {
    setSelectedDialog(dialog);
  };
  
  // Handle creating a new dialog
  const handleCreateDialog = async () => {
    if (!currentChat || !initDataRaw || isCreatingDialog) {
      return;
    }
    
    try {
      setIsCreatingDialog(true);
      
      const newDialog = await createDialog({
        chat_id: currentChat.id,
        user_id: '' // Will be set by the backend from auth
      }, initDataRaw);
      
      if (newDialog) {
        setSelectedDialog(newDialog);
      }
    } catch (error) {
      console.error('Failed to create dialog:', error);
    } finally {
      setIsCreatingDialog(false);
    }
  };
  
  // Handle sending a message
  const handleSendMessage = async (dialogId: string, content: string) => {
    if (!initDataRaw) {
      return;
    }
    
    // Get user preferences from store
    const userData = useUserStore.getState().user;
    const dialogContextLength = userData?.preferred_message_context_size || DEFAULT_CONTEXT_SIZE;
    const modelName = userData?.preferred_ai_model || DEFAULT_MODEL;
    
    // Create message request with all required fields
    const messageRequest: LangChainMessageRequest = {
      dialog_id: dialogId,
      content,
      dialog_context_length: dialogContextLength,
      model_name: modelName,
      temperature: 0.5,
      prompt_template: "base_tg_prompt",
      max_tokens: DEFAULT_MAX_TOKENS
    };
    
    console.log("Sending message with user preferences:", messageRequest);
    
    // Call the sendMessage function with the complete request object
    await sendMessage(messageRequest, initDataRaw);
  };
  
  // Handle back navigation - use replace instead of push to avoid adding to history
  const handleBackToChats = () => {
    // Use replace instead of push to avoid adding to history
    router.replace('/');
  };
  
  // Handle settings click - store current location in sessionStorage
  const handleSettingsClick = () => {
    // Save the current chat ID in sessionStorage to return here from settings
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('previousChatId', chatId);
    }
    
    // Navigate to settings
    router.push('/settings');
  };
  
  if (chatLoading || !currentChat) {
    return (
      <Page back onBack={handleBackToChats}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }
  
  if (chatError) {
    return (
      <Page back onBack={handleBackToChats}>
        <div className="alert alert-error shadow-lg mx-4 my-6">
          <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="font-bold">Error</h3>
            <div className="text-sm">{chatError}</div>
          </div>
        </div>
      </Page>
    );
  }
  
  const chatTitle = currentChat.title || `Chat ${currentChat.telegram_id}`;
  
  return (
    <Page back onBack={handleBackToChats}>
      <Header 
        title={chatTitle}
        onSettingsClick={handleSettingsClick}
      />
      <div className="container mx-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Left sidebar - List of dialogs */}
          <div className="md:col-span-1 bg-base-200 p-4 rounded-box">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">AI Dialogs</h2>
              <button 
                className="btn btn-primary btn-sm"
                onClick={handleCreateDialog}
                disabled={isCreatingDialog}
              >
                {isCreatingDialog ? (
                  <span className="loading loading-spinner loading-xs"></span>
                ) : (
                  'New Dialog'
                )}
              </button>
            </div>
            
            {dialogsLoading && dialogs.length === 0 ? (
              <div className="flex justify-center p-4">
                <Preloader />
              </div>
            ) : (
              <AIDialogList 
                dialogs={dialogs} 
                onDialogClick={handleDialogClick}
                selectedDialogId={selectedDialog?.id}
              />
            )}
            
            {dialogsError && (
              <div className="alert alert-error mt-4">
                <div>
                  <span>{dialogsError}</span>
                </div>
              </div>
            )}
          </div>
          
          {/* Right panel - Current dialog */}
          <div className="md:col-span-2 bg-base-200 rounded-box p-4 flex flex-col h-[70vh]">
            {!selectedDialog ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <h3 className="text-xl font-bold mb-2">No Dialog Selected</h3>
                <p className="text-base-content text-opacity-60 mb-4">Select an existing dialog or create a new one to start chatting.</p>
                <button 
                  className="btn btn-primary"
                  onClick={handleCreateDialog}
                  disabled={isCreatingDialog}
                >
                  {isCreatingDialog ? (
                    <span className="loading loading-spinner loading-xs mr-2"></span>
                  ) : null}
                  Create New Dialog
                </button>
              </div>
            ) : (
              <>
                {/* Dialog header */}
                <div className="border-b border-base-300 pb-2 mb-4">
                  <h3 className="text-lg font-bold">
                    Dialog #{selectedDialog.id.substring(0, 8)}
                  </h3>
                </div>
                
                {/* Messages container */}
                <div className="flex-1 overflow-y-auto mb-4 px-2">
                  {dialogsLoading && !currentDialog ? (
                    <div className="flex justify-center p-4">
                      <Preloader />
                    </div>
                  ) : currentDialog && currentDialog.messages.length > 0 ? (
                    <div className="space-y-4">
                      {currentDialog.messages.map((message) => (
                        <AIMessage key={message.id} message={message} />
                      ))}
                    </div>
                  ) : (
                    <div className="alert alert-info">
                      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                      <span>This dialog has no messages. Start the conversation by sending a message below.</span>
                    </div>
                  )}
                </div>
                
                {/* Message input */}
                <div className="mt-auto">
                  <MessageInput 
                    dialogId={selectedDialog.id} 
                    onSendMessage={handleSendMessage}
                    initDataRaw={initDataRaw}
                    isFirstMessage={!currentDialog?.messages.length}
                    disabled={dialogsLoading} 
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </Page>
  );
} 