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
import { useWebSocket } from '@/hooks/useWebSocket';
import { Button } from '@/components/ui/button';
import DraftCard from '@/components/DraftCard';
import Pager from '@/components/Pager';
import ContextBubble from '@/components/ContextBubble';
import { Post } from '@/core/api/services/post-service';

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
  const [feedSource, setFeedSource] = useState<'channels' | 'groups' | 'both'>('channels');
  const { drafts, fetchDrafts, updateDraft, approveDraft, postDraft, regenerateDraft, generateDraftComment, upsertDraft } = useCommentStore();
  const { lastMessage } = useWebSocket({ userId: useUserStore.getState().user?.id, initDataRaw: 'mock_init_data_for_telethon' });

  const [selectedChat, setSelectedChat] = useState<TelegramChat | null>(null);
  const [editingDrafts, setEditingDrafts] = useState<Record<string, string>>({});
  const [regenFeedback, setRegenFeedback] = useState<Record<string, string>>({});
  const [openBubbleKey, setOpenBubbleKey] = useState<string | null>(null);
  const [styleMemoryOpen, setStyleMemoryOpen] = useState<string | null>(null);

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
        console.log('[Page] loadData started');
        
        const mockInitDataRaw = "mock_init_data_for_telethon";
        
        await fetchUser(mockInitDataRaw);
        const userData = useUserStore.getState().user;
        const limit = userData?.telegram_chats_load_limit || DEFAULT_CHAT_LOAD_LIMIT;
        await fetchChats(mockInitDataRaw, limit);
          await fetchPosts(mockInitDataRaw, 1, 20, feedSource);
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
  }, [fetchUser, fetchChats, fetchPosts, fetchDrafts, feedSource]);

  // Realtime: append new drafts without refresh
  useEffect(() => {
    if (!lastMessage) return;
    if (lastMessage.event === 'new_ai_draft' && lastMessage.data?.draft) {
      try {
        const d = lastMessage.data.draft as DraftComment;
        upsertDraft(d);
      } catch {}
    }
  }, [lastMessage, upsertDraft]);

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

  // Ensure unique posts by DB id to avoid duplicate keys from backend duplicates
  const uniquePosts = useMemo(() => {
    const map = new Map<string, Post>();
    for (const p of posts) {
      const key = String(p.id);
      if (!map.has(key)) map.set(key, p);
    }
    return Array.from(map.values());
  }, [posts]);

  // Draft items to render on main page (show drafts even if no matching post found)
  const draftItems = useMemo(() => {
    // Keep only the latest draft per original_message_id
    const latestByMsgId = new Map<string, DraftComment>();
    const toTs = (d: DraftComment) => {
      const c = new Date(d.created_at).getTime();
      const u = new Date(d.updated_at || d.created_at).getTime();
      return Math.max(c || 0, u || 0);
    };
    // Sort ascending by timestamp so the last write wins in the map
    const sortedDrafts = [...drafts].sort((a, b) => toTs(a) - toTs(b));
    for (const d of sortedDrafts) {
      const key = String(d.original_message_id);
      const prev = latestByMsgId.get(key);
      if (!prev) { latestByMsgId.set(key, d); continue; }
      const prevTs = toTs(prev);
      const curTs = toTs(d);
      // Prefer newer by timestamp; on tie prefer current
      if (curTs >= prevTs) {
        latestByMsgId.set(key, d);
      }
    }

    // Prefer aligning to the current page's posts so channel names and context are present
    const alignedRaw = uniquePosts
      .map((p) => {
        const d = latestByMsgId.get(String(p.id));
        return d ? ({ post: p, draft: d } as { draft: DraftComment; post: Post }) : null;
      })
      .filter(Boolean) as { draft: DraftComment; post: Post }[];
    // Deduplicate by draft id in case of accidental duplicates
    const seen = new Set<string>();
    const aligned = alignedRaw.filter(({ draft }) => {
      if (seen.has(draft.id)) return false;
      seen.add(draft.id);
      return true;
    });
    if (aligned.length > 0) {
      return aligned;
    }

    // Fallback: previous behavior (for pages without matched drafts)
    const items = Array.from(latestByMsgId.values()).map((draft) => {
      const matchedPost = uniquePosts.find((p) => String(p.id) === String(draft.original_message_id));
      return { draft, post: matchedPost } as { draft: DraftComment; post: Post | undefined };
    });
    return items.sort(
      (a, b) => new Date(b.draft.updated_at || b.draft.created_at).getTime() - new Date(a.draft.updated_at || a.draft.created_at).getTime()
    );
  }, [posts, drafts]);

  // Posts on current page that don't have a draft yet
  const postsWithoutDraft = useMemo(() => {
    const hasDraftByMsgId = new Set(draftItems.map(i => String(i.draft.original_message_id)));
    const filtered = uniquePosts.filter(p => !hasDraftByMsgId.has(String(p.id)));
    // Deduplicate again defensively by id to prevent duplicate keys
    const map = new Map<string, Post>();
    for (const p of filtered) map.set(String(p.id), p);
    return Array.from(map.values());
  }, [uniquePosts, draftItems]);

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
    const payload = post
      ? { id: post.id, telegram_id: post.telegram_id, original_message_id: String(post.id), text: post.text, channel_telegram_id: post.channel_telegram_id }
      : { original_message_id: String(draft.original_message_id), text: draft.original_post_content } as any;
    await regenerateDraft(
      draft.id,
      payload,
      feedback,
      'mock_init_data_for_telethon'
    );
    setRegenFeedback((prev) => ({ ...prev, [draft.id]: '' }));
    // Clear any local edit override so refreshed draft text is visible
    setEditingDrafts((prev) => {
      const copy = { ...prev };
      delete copy[draft.id];
      return copy;
    });
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
        {/* Feed source toggle (top-centered) */}
        <div className="flex items-center justify-center gap-2 mb-4">
          <span className="text-sm text-gray-400">Source:</span>
          {(['channels','both','groups'] as const).map(s => (
            <button
              key={s}
              className={`px-2 py-1 rounded text-sm ${feedSource === s ? 'bg-blue-600 text-white' : 'bg-black/20 border border-white/10 text-gray-200'}`}
              onClick={() => setFeedSource(s)}
            >
              {s === 'channels' ? 'Channels' : s === 'both' ? 'Both' : 'Groups'}
            </button>
          ))}
        </div>

        <div className="mb-6">
          {/* Drafts matched to posts */}
          <div className="space-y-6">
            {draftItems.map(({ post, draft }) => (
              <DraftCard
                key={draft.id}
                post={post}
                draft={draft}
                editingText={editingDrafts[draft.id]}
                feedback={regenFeedback[draft.id]}
                openBubbleKey={openBubbleKey}
                onChangeText={(text) => handleEditChange(draft.id, text)}
                onSend={() => handleSend(draft.id)}
                onRegenerate={() => handleRegenerate(draft, post)}
                onToggleChannelCtx={() => setOpenBubbleKey((prev) => (prev === `chan:${draft.id}` ? null : `chan:${draft.id}`))}
                onToggleMsgCtx={() => setOpenBubbleKey((prev) => (prev === `msg:${draft.id}` ? null : `msg:${draft.id}`))}
                onCtxChange={(fieldKey, value) => handleEditChange(fieldKey, value)}
                onCtxSave={() => handleSaveEdit(draft.id)}
                onCtxClose={() => setOpenBubbleKey(null)}
              />
            ))}
            {/* Posts without drafts yet */}
            {postsWithoutDraft.map((post) => (
              <div key={`postonly-${post.id}`} className="card tg-post border border-white/10">
                <div className="card-body">
                  <div className="mb-2 text-sm text-muted-foreground">{post.channel?.title || 'Channel'} · {new Date(post.date).toLocaleString()}</div>
                  {post.media_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={post.media_url} alt="post media" className="mb-3 max-h-96 w-auto rounded" />
                  ) : null}
                  <div className="mb-3 whitespace-pre-wrap text-sm">{post.text || (post.media_url ? 'Media post' : 'Media post')}</div>
                  <div className="flex justify-end">
                    <button
                      className="btn btn-sm btn-outline"
                      onClick={() => generateDraftComment(post.telegram_id, post.channel_telegram_id || 0, 'mock_init_data_for_telethon')}
                    >
                      Generate draft
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pagination - centered bottom controls */}
        <Pager
          currentPage={currentPage}
          totalPages={totalPages}
          onPage={(p) => fetchPosts('mock_init_data_for_telethon', p, 20, feedSource)}
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



