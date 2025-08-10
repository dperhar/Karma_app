'use client';

import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { ChangeEvent, useEffect, useMemo, useState } from 'react';

import { ChatList } from '@/components/ChatList';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { TelegramAuthModal } from '@/components/TelegramAuthModal/TelegramAuthModal';
import { useChatStore } from '@/store/chatStore';
import { useUserStore } from '@/store/userStore';
import { TelegramChat, TelegramMessengerChatType } from '@/types/chat';
import { usePostStore } from '@/store/postStore';
import { useCommentStore, DraftComment } from '@/store/commentStore';
import { Button } from '@/components/ui/button';
import DraftCard from '@/components/DraftCard';
import Pager from '@/components/Pager';
import ContextBubble from '@/components/ContextBubble';
import { Post } from '@/core/api/services/post-service';
import GeneratingNotice from '@/components/GeneratingNotice';

// Define filter types
type FilterType = 'all' | 'private' | 'group' | 'channel';

// Default chat load limit if not set in user preferences
const DEFAULT_CHAT_LOAD_LIMIT = 50;

export default function Home() {
  const t = useTranslations('i18n');
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);
  
  const { fetchUser, user, isLoading: userLoading, error: userError } = useUserStore();
  const { fetchChats, chats, isLoading: chatsLoading, error: chatsError } = useChatStore();
  const { posts, fetchPosts, currentPage, totalPages } = usePostStore();
  const { drafts, fetchDrafts, updateDraft, approveDraft, postDraft, regenerateDraft, queueDraftsForPosts } = useCommentStore();

  const [selectedChat, setSelectedChat] = useState<TelegramChat | null>(null);
  const [editingDrafts, setEditingDrafts] = useState<Record<string, string>>({});
  const [regenFeedback, setRegenFeedback] = useState<Record<string, string>>({});
  const [openBubbleKey, setOpenBubbleKey] = useState<string | null>(null);
  const [styleMemoryOpen, setStyleMemoryOpen] = useState<string | null>(null);

  const router = useRouter();
  const [pageState, setPageState] = useState<number>(1);

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
        console.log('[Page] loadData started');
        
        const mockInitDataRaw = "mock_init_data_for_telethon";
        
        await fetchUser(mockInitDataRaw);
        const userData = useUserStore.getState().user;
        const limit = userData?.telegram_chats_load_limit || DEFAULT_CHAT_LOAD_LIMIT;
        await fetchChats(mockInitDataRaw, limit);
        await fetchPosts(mockInitDataRaw, 1, 30, { bustCache: true, queueMissing: true });
        await fetchDrafts(mockInitDataRaw);
        
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

    const isSessionAuthenticated = typeof window !== 'undefined' && 
      sessionStorage.getItem("env-authenticated") === "1";
    
    if (isSessionAuthenticated) {
      console.log('[Page] Starting data load - user authenticated via session...');
      loadData();
    } else {
      console.log('[Page] Not loading data - user not authenticated');
    }
    
    return () => {
      isMounted = false;
    };
  }, [fetchUser, fetchChats, fetchPosts, fetchDrafts]);

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

  // Draft items to render – scoped to CURRENT PAGE posts only
  const draftItems = useMemo(() => {
    if (!posts?.length) return [] as { post: Post; draft: DraftComment }[];
    // Build latest draft per message id
    const latestByMsgId = new Map<string, DraftComment>();
    for (const d of drafts) {
      const key = String(d.original_message_id);
      const prev = latestByMsgId.get(key);
      const prevTs = prev ? new Date(prev.updated_at || prev.created_at).getTime() : -1;
      const curTs = new Date(d.updated_at || d.created_at).getTime();
      if (!prev || curTs >= prevTs) latestByMsgId.set(key, d);
    }
    // Pair each page post with its draft (by telegram_id or db id)
    const items: { post: Post; draft: DraftComment }[] = [];
    for (const p of posts) {
      const candIds = [String(p.telegram_id), String(p.id)];
      let found: DraftComment | undefined;
      for (const id of candIds) {
        const d = latestByMsgId.get(id);
        if (d) { found = d; break; }
      }
      if (found) items.push({ post: p, draft: found });
    }
    return items;
  }, [posts, drafts]);

  // Show generating notice only when the current page has posts but no matching latest drafts
  // Build a set of latest draft keys for quick lookup
  const latestDraftKeySet = useMemo(() => {
    const latestByMsgId = new Map<string, DraftComment>();
    for (const d of drafts) {
      const key = String(d.original_message_id);
      const prev = latestByMsgId.get(key);
      const prevTs = prev ? new Date(prev.updated_at || prev.created_at).getTime() : -1;
      const curTs = new Date(d.updated_at || d.created_at).getTime();
      if (!prev || curTs >= prevTs) latestByMsgId.set(key, d);
    }
    return new Set(Array.from(latestByMsgId.keys()));
  }, [drafts]);

  const isGeneratingForPage = useMemo(() => {
    if (!posts?.length) return false;
    // Show notice only if NONE of the posts have drafts yet
    for (const p of posts) {
      if (latestDraftKeySet.has(String(p.telegram_id)) || latestDraftKeySet.has(String(p.id))) {
        return false;
      }
    }
    return true;
  }, [posts, latestDraftKeySet]);

  useEffect(() => {
    // Queue generation for any post on the page that lacks a draft (even if some have drafts)
    if (!posts.length) return;
    const missing = posts.filter(
      (p) => !latestDraftKeySet.has(String(p.telegram_id)) && !latestDraftKeySet.has(String(p.id))
    );
    if (missing.length) {
      const payload = missing.map((p) => ({
        original_message_id: String(p.id),
        original_post_content: p.text,
        original_post_url: p.url,
        channel_telegram_id: p.channel_telegram_id,
      }));
      queueDraftsForPosts(payload, 'mock_init_data_for_telethon');
    }
  }, [posts, latestDraftKeySet, queueDraftsForPosts]);

  const handleEditChange = (draftId: string, text: string) => {
    // Support nested context edits using keys like `${id}::channel_context`
    const [baseId, field] = draftId.split('::');
    if (field) {
      // Store temporary context/style edits in regenFeedback map to merge on save
      setRegenFeedback(prev => ({ ...prev, [`ctx:${baseId}:${field}`]: text }));
    } else {
      setEditingDrafts(prev => ({ ...prev, [draftId]: text }));
    }
  };

  const handleSaveEdit = async (draftId: string) => {
    const text = editingDrafts[draftId];
    // Merge any context edits staged in regenFeedback under keys `ctx:${draftId}:<field>`
    const gp: Record<string, any> = {};
    for (const [k, v] of Object.entries(regenFeedback)) {
      if (k.startsWith(`ctx:${draftId}:`)) {
        const field = k.split(':')[2];
        // Convert boolean strings for style flag
        if (field === 'is_style_example') {
          gp[field] = String(v).toLowerCase() === 'true';
        } else {
          gp[field] = v;
        }
      }
    }
    await updateDraft(draftId, text ?? '', 'mock_init_data_for_telethon', Object.keys(gp).length ? gp : undefined);
  };

  const handleApprove = async (draftId: string) => {
    await approveDraft(draftId, 'mock_init_data_for_telethon');
  };

  const handlePost = async (draftId: string) => {
    await postDraft(draftId, 'mock_init_data_for_telethon');
  };

  // Local inline removed; we use components/ContextBubble.tsx

  const handleRegenerate = async (draft: DraftComment, post?: Post) => {
    const feedback = regenFeedback[draft.id];
    const fallbackTelegramId = Number.isFinite(Number(draft.original_message_id))
      ? Number(draft.original_message_id)
      : 0;
    await regenerateDraft(
      draft.id,
      { telegram_id: post?.telegram_id ?? fallbackTelegramId, text: post?.text ?? draft.original_post_content },
      feedback,
      'mock_init_data_for_telethon'
    );
    setRegenFeedback((prev) => ({ ...prev, [draft.id]: '' }));
  };

  const handleSend = async (draftId: string) => {
    // Persist current edits (text + any staged context) before sending
    await handleSaveEdit(draftId);
    await postDraft(draftId, 'mock_init_data_for_telethon');
  };

  // Handle Telegram authentication success
  const handleTelegramAuthSuccess = async () => {
    console.log('[Page] Telegram authentication successful, reloading data...');
    setShowAuthModal(false);
    
    // Reload chats with real authentication
    const mockInitDataRaw = "mock_init_data_for_telethon";
    await fetchChats(mockInitDataRaw, user?.telegram_chats_load_limit || DEFAULT_CHAT_LOAD_LIMIT);
  };

  // Handle connect to Telegram button
  const handleConnectTelegram = () => {
    console.log('[Page] Connect to Telegram button clicked');
    setShowAuthModal(true);
  };

  // Test function to force reload chats
  const handleForceReloadChats = async () => {
    console.log('[Page] Force reload chats button clicked');
    const isSessionAuthenticated = typeof window !== 'undefined' && 
      sessionStorage.getItem("env-authenticated") === "1";
    
    if (isSessionAuthenticated) {
      console.log('[Page] Session authenticated, calling fetchChats with mock initDataRaw');
      await fetchChats("mock_init_data_for_telethon", 20);
    } else {
      console.log('[Page] No session authentication available');
    }
  };

  return (
    <Page 
      back={!!selectedChat} 
      onBack={handleBackNavigation}
    >
      <Header title="AI Draft Feed" onSettingsClick={handleSettingsClick} />
      <div className="container mx-auto p-4 tg-feed">
        <div className="mb-6 space-y-6">
          {isGeneratingForPage && (
            <GeneratingNotice />
          )}
          {/* Drafts list on main page */}
          <div className="space-y-6">
            {posts.map((post) => {
              const pair = draftItems.find((x) => String(x.post.id) === String(post.id));
              const draft = pair?.draft;
              return (
              <DraftCard
                key={post.id}
                post={post}
                draft={draft}
                editingText={draft ? editingDrafts[draft.id] : ''}
                feedback={draft ? regenFeedback[draft.id] : ''}
                openBubbleKey={openBubbleKey}
                onChangeText={(text) => draft && handleEditChange(draft.id, text)}
                onSend={() => draft && handleSend(draft.id)}
                onRegenerate={() => draft && handleRegenerate(draft, post)}
                onToggleChannelCtx={() => draft && setOpenBubbleKey((prev) => (prev === `chan:${draft.id}` ? null : `chan:${draft.id}`))}
                onToggleMsgCtx={() => draft && setOpenBubbleKey((prev) => (prev === `msg:${draft.id}` ? null : `msg:${draft.id}`))}
                onCtxChange={(fieldKey, value) => handleEditChange(fieldKey, value)}
                onCtxSave={() => draft && handleSaveEdit(draft.id)}
                onCtxClose={() => setOpenBubbleKey(null)}
              />
              );
            })}
          </div>
        </div>

        {/* Pagination - centered bottom controls */}
        <Pager
          currentPage={currentPage}
          totalPages={totalPages}
          onPage={(p) => {
            setPageState(p);
            fetchPosts('mock_init_data_for_telethon', p, 30, { queueMissing: true });
          }}
        />

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

      {/* Telegram Authentication Modal */}
      <TelegramAuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initDataRaw="mock_init_data_for_telethon"
        onSuccess={handleTelegramAuthSuccess}
      />
    </Page>
  );
}



