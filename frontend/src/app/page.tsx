'use client';

import { initData, useSignal } from '@telegram-apps/sdk-react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { ChangeEvent, useEffect, useMemo, useState } from 'react';

import { ChatList } from '@/components/ChatList';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { useChatStore } from '@/store/chatStore';
import { useUserStore } from '@/store/userStore';
import { TelegramChat, TelegramMessengerChatType } from '@/types/chat';

// Define filter types
type FilterType = 'all' | 'private' | 'group' | 'channel';

// Default chat load limit if not set in user preferences
const DEFAULT_CHAT_LOAD_LIMIT = 50;

export default function Home() {
  const t = useTranslations('i18n');
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  // Get the Telegram initialization data
  const initDataRaw = useSignal(initData.raw);
  const initDataState = useSignal(initData.state);
  
  const { fetchUser, user, isLoading: userLoading, error: userError } = useUserStore();
  const { fetchChats, chats, isLoading: chatsLoading, error: chatsError } = useChatStore();

  const [selectedChat, setSelectedChat] = useState<TelegramChat | null>(null);

  const router = useRouter();

  // First filter by search query
  const searchedChats = useMemo(() => {
    if (!searchQuery.trim()) {
      return chats;
    }
    
    const normalizedQuery = searchQuery.toLowerCase().trim();
    return chats.filter(chat => {
      const title = (chat.title || `Chat ${chat.telegram_id}`).toLowerCase();
      return title.includes(normalizedQuery);
    });
  }, [chats, searchQuery]);

  // Then filter by category
  const filteredChats = useMemo(() => {
    if (activeFilter === 'all') {
      return searchedChats;
    } else if (activeFilter === 'private') {
      return searchedChats.filter(chat => chat.type === TelegramMessengerChatType.PRIVATE);
    } else if (activeFilter === 'group') {
      return searchedChats.filter(chat => 
        chat.type === TelegramMessengerChatType.GROUP || 
        chat.type === TelegramMessengerChatType.SUPERGROUP
      );
    } else if (activeFilter === 'channel') {
      return searchedChats.filter(chat => chat.type === TelegramMessengerChatType.CHANNEL);
    }
    return searchedChats;
  }, [searchedChats, activeFilter]);

  // Handle search input change
  const handleSearchChange = (e: ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Clear search
  const handleClearSearch = () => {
    setSearchQuery('');
  };

  // Initial data loading
  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        console.log('[Page] loadData started - initDataRaw value:', initDataRaw?.substring(0, 50) + '...');
        console.log('[Page] loadData started - initDataState value:', initDataState);
        
        // Check if we have valid initialization data
        if (!initDataRaw) {
          console.error('[Page] No Telegram init data available');
          return;
        }
        
        // Fetch fresh user data from server first
        console.log('[Page] Fetching fresh user data from server');
        await fetchUser(initDataRaw);
        
        // Get the latest user data which includes their chat load limit preference
        const userData = useUserStore.getState().user;
        const limit = userData?.telegram_chats_load_limit || DEFAULT_CHAT_LOAD_LIMIT;
        
        // Fetch chats with the user's preferred limit
        console.log(`[Page] Loading chats with user-defined limit: ${limit}`);
        await fetchChats(initDataRaw, limit);
        
        // Log current state after fetch
        const chatState = useChatStore.getState();
        console.log('[Page] After fetchChats - chatState:', {
          chatsCount: chatState.chats?.length || 0,
          isLoading: chatState.isLoading,
          error: chatState.error,
          firstFewChats: chatState.chats?.slice(0, 3)
        });
        
      } catch (err) {
        console.error('[Page] Failed to load data:', err);
      } finally {
        if (isMounted) {
          console.log('[Page] Setting loading to false');
          setLoading(false);
        }
      }
    };

    // Only proceed with data loading if initialization data is available
    if (initDataState && initDataRaw) {
      console.log('[Page] Starting data load...');
      loadData();
    } else {
      console.log('[Page] Not loading data - missing initData:', { initDataState, hasInitDataRaw: !!initDataRaw });
    }
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [fetchUser, fetchChats, initDataRaw, initDataState]);

  const handleChatClick = (chat: TelegramChat) => {
    setSelectedChat(chat);
    // Navigate to the chat detail page
    router.push(`/chat/${chat.telegram_id}`);
  };

  // Handle back button navigation
  const handleBackNavigation = () => {
    setSelectedChat(null);
  };

  // Handle settings click navigation
  const handleSettingsClick = () => {
    router.push('/settings');
  };

  // Handle comments click navigation
  const handleCommentsClick = () => {
    router.push('/comments');
  };

  // Handle AI comments click navigation
  const handleAICommentsClick = () => {
    router.push('/ai-comments');
  };

  // Get chat counts by type
  const chatCounts = useMemo(() => {
    console.log('[Page] Calculating chatCounts - searchedChats:', searchedChats?.length || 0);
    // Use searchedChats to include only chats that match the search
    const privateCount = searchedChats.filter(chat => chat.type === TelegramMessengerChatType.PRIVATE).length;
    const groupCount = searchedChats.filter(chat => 
      chat.type === TelegramMessengerChatType.GROUP || 
      chat.type === TelegramMessengerChatType.SUPERGROUP
    ).length;
    const channelCount = searchedChats.filter(chat => chat.type === TelegramMessengerChatType.CHANNEL).length;
    
    const counts = {
      all: searchedChats.length,
      private: privateCount,
      group: groupCount,
      channel: channelCount
    };
    
    console.log('[Page] Chat counts:', counts);
    return counts;
  }, [searchedChats]);

  console.log('[Page] Render - Current state:', {
    loading,
    userLoading,
    chatsLoading,
    userError,
    chatsError,
    chatsCount: chats?.length || 0,
    filteredChatsCount: filteredChats?.length || 0,
    activeFilter,
    searchQuery
  });

  if (loading || userLoading || chatsLoading) {
    console.log('[Page] Showing loading state');
    return (
      <Page back={false}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }

  if (userError || chatsError) {
    console.log('[Page] Showing error state:', { userError, chatsError });
    return (
      <Page back={false}>
        <div className="alert alert-error shadow-lg mx-4 my-6">
          <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="font-bold">Error</h3>
            <div className="text-sm">{userError || chatsError}</div>
          </div>
        </div>
      </Page>
    );
  }

  console.log('[Page] Rendering main content with filteredChats:', filteredChats?.length || 0);

  // Test function to force reload chats
  const handleForceReloadChats = async () => {
    console.log('[Page] Force reload chats button clicked');
    if (initDataRaw) {
      console.log('[Page] initDataRaw available, calling fetchChats');
      await fetchChats(initDataRaw, 20);
    } else {
      console.log('[Page] No initDataRaw available');
    }
  };

  return (
    <Page 
      back={!!selectedChat} 
      onBack={handleBackNavigation}
    >
      <Header 
        title="Your Chats"
        onSettingsClick={handleSettingsClick}
      />
      <div className="container mx-auto p-4">
        {/* Диагностическая информация */}
        <div className="alert alert-info mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
          </svg>
          <div>
            <h3 className="font-bold">Диагностика:</h3>
            <div className="text-xs">
              <p>Всего чатов: {chats?.length || 0}</p>
              <p>Отфильтрованных чатов: {filteredChats?.length || 0}</p>
              <p>Поисковый запрос: "{searchQuery}"</p>
              <p>Активный фильтр: {activeFilter}</p>
              <p>Загрузка: {loading ? 'да' : 'нет'} | Загрузка чатов: {chatsLoading ? 'да' : 'нет'}</p>
              <p>Ошибки: {chatsError || 'нет'}</p>
              <p>initDataRaw доступен: {initDataRaw ? 'да' : 'нет'}</p>
              <p>initDataState: {initDataState ? 'да' : 'нет'}</p>
            </div>
            <button 
              className="btn btn-sm btn-primary mt-2"
              onClick={handleForceReloadChats}
              disabled={chatsLoading}
            >
              {chatsLoading ? 'Загружаем...' : 'Принудительно загрузить чаты'}
            </button>
          </div>
        </div>
        
        {/* Navigation buttons */}
        <div className="flex gap-2 mb-6">
          <button 
            className="btn btn-primary flex-1"
            onClick={handleAICommentsClick}
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            AI Comment Manager
          </button>
          <button 
            className="btn btn-outline flex-1"
            onClick={handleCommentsClick}
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Manual Comments
          </button>
        </div>
        
        <div className="mb-6">

          
          {/* Search bar */}
          <div className="form-control mb-4">
            <div className="relative w-full">
              <input 
                type="text" 
                placeholder="Поиск чатов..." 
                className="input input-bordered w-full pr-20"
                value={searchQuery}
                onChange={handleSearchChange}
              />
              <div className="absolute inset-y-0 right-0 flex items-center">
                {searchQuery && (
                  <button 
                    className="btn btn-ghost btn-sm px-2"
                    onClick={handleClearSearch}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                <button className="btn btn-ghost btn-sm px-3 mr-1">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          {/* Chat filter tabs */}
          <div className="tabs tabs-boxed bg-base-200 mb-4">
            <a 
              className={`tab ${activeFilter === 'all' ? 'tab-active' : ''}`}
              onClick={() => setActiveFilter('all')}
            >
              Все
              <span className="badge badge-sm ml-1">{chatCounts.all}</span>
            </a>
            <a 
              className={`tab ${activeFilter === 'private' ? 'tab-active' : ''}`}
              onClick={() => setActiveFilter('private')}
            >
              Чаты
              <span className="badge badge-sm ml-1">{chatCounts.private}</span>
            </a>
            <a 
              className={`tab ${activeFilter === 'group' ? 'tab-active' : ''}`}
              onClick={() => setActiveFilter('group')}
            >
              Группы
              <span className="badge badge-sm ml-1">{chatCounts.group}</span>
            </a>
            <a 
              className={`tab ${activeFilter === 'channel' ? 'tab-active' : ''}`}
              onClick={() => setActiveFilter('channel')}
            >
              Каналы
              <span className="badge badge-sm ml-1">{chatCounts.channel}</span>
            </a>
          </div>
          
          {/* No results message */}
          {filteredChats.length === 0 && searchQuery && (
            <div className="alert alert-info shadow-lg mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current flex-shrink-0 w-6 h-6">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <div>
                <span>По запросу &ldquo;{searchQuery}&rdquo; ничего не найдено в категории &ldquo;{
                  activeFilter === 'all' ? 'Все' : 
                  activeFilter === 'private' ? 'Чаты' : 
                  activeFilter === 'group' ? 'Группы' : 'Каналы'
                }&rdquo;</span>
              </div>
            </div>
          )}
          
          <ChatList 
            chats={filteredChats} 
            onChatClick={handleChatClick}
            selectedChat={selectedChat}
          />
        </div>

        {selectedChat && (
          <div className="card bg-base-200 shadow-lg">
            <div className="card-body">
              <h3 className="card-title text-base-content flex items-center">
                <div className="badge badge-primary mr-2">{selectedChat.type}</div>
                {selectedChat.title || `Chat ${selectedChat.telegram_id}`}
              </h3>
              <div className="divider my-2"></div>
              <div className="stats stats-vertical sm:stats-horizontal shadow bg-base-100">
                <div className="stat">
                  <div className="stat-title">ID</div>
                  <div className="stat-value text-lg">{selectedChat.telegram_id}</div>
                </div>
                {selectedChat.member_count && (
                  <div className="stat">
                    <div className="stat-title">Members</div>
                    <div className="stat-value text-lg">{selectedChat.member_count}</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Page>
  );
}



