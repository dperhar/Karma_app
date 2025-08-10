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
  const { drafts, fetchDrafts, updateDraft, approveDraft, postDraft, regenerateDraft } = useCommentStore();

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
          await fetchPosts(mockInitDataRaw, 1, 30);
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

  // Draft items to render on main page (show drafts even if no matching post found)
  const draftItems = useMemo(() => {
    // Keep only the latest draft per original_message_id
    const latestByMsgId = new Map<string, DraftComment>();
    for (const d of drafts) {
      const key = String(d.original_message_id);
      const prev = latestByMsgId.get(key);
      const prevTs = prev ? new Date(prev.updated_at || prev.created_at).getTime() : -1;
      const curTs = new Date(d.updated_at || d.created_at).getTime();
      if (!prev || curTs >= prevTs) {
        latestByMsgId.set(key, d);
      }
    }

    const items = Array.from(latestByMsgId.values()).map((draft) => {
      const matchedPost = posts.find((p) => String(p.telegram_id) === String(draft.original_message_id));
      return { draft, post: matchedPost } as { draft: DraftComment; post: Post | undefined };
    });
    // Sort by latest draft timestamp desc
    return items.sort(
      (a, b) => new Date(b.draft.updated_at || b.draft.created_at).getTime() - new Date(a.draft.updated_at || a.draft.created_at).getTime()
    );
  }, [posts, drafts]);

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

  const ContextBubble: React.FC<{ id: string; label: string; value: string; onChange: (v: string) => void; onSave: () => void; isOpen: boolean; onClose: () => void; }>=({ id, label, value, onChange, onSave, isOpen, onClose })=>{
    if (!isOpen) return null;
    return (
      <div className="absolute bottom-full left-0 mb-2 z-50">
        <div className="rounded-xl shadow-xl border border-border bg-base-100 p-3"
             style={{ minWidth: '10rem', minHeight: '5rem', maxWidth: '25vw', maxHeight: '25vh' }}>
          <div className="flex items-center mb-2 text-xs opacity-70">
            <span className="font-medium mr-2">{label}</span>
            <button className="ml-auto btn btn-ghost btn-xs" onClick={onClose}>✕</button>
          </div>
          <textarea
            className="w-full bg-transparent outline-none text-sm resize-none overflow-auto"
            style={{ maxHeight: '20vh' }}
            value={value}
            onChange={(e)=>onChange(e.target.value)}
            rows={5}
          />
          <div className="mt-2 text-right">
            <button className="btn btn-xs btn-primary" onClick={onSave}>Save</button>
          </div>
        </div>
      </div>
    );
  };

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
        <div className="mb-6">
          {/* Drafts list on main page */}
          <div className="space-y-6">
            {draftItems.map(({ post, draft }) => (
              <div key={draft.id} className="card tg-post">
                <div className="card-body">
                  {post ? (
                    <div className="mb-3">
                      <div className="tg-post-header">
                        <div className="tg-avatar">
                          {post.channel.avatar_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={(post.channel as any).avatar_url} alt="avatar" className="h-full w-full object-cover" />
                          ) : (
                            (() => {
                              const name = post.channel.title || '';
                              const initials = name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();
                              return initials || '•';
                            })()
                          )}
                        </div>
                        <span className="tg-post-title">{post.channel.title}</span>
                        <span>·</span>
                        <span>{new Date(post.date).toLocaleString()}</span>
                        {typeof post.replies === 'number' && (
                          <span className="ml-auto">Replies: {post.replies}</span>
                        )}
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{post.text}</p>
                      {Array.isArray(post.reactions) && post.reactions.length > 0 && (
                        <div className="mt-2 tg-reactions flex flex-wrap gap-2 opacity-80">
                          {post.reactions.map((r, idx) => (
                            <span key={idx}>{(r.emoticon || (r.reaction as any))} {r.count}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mb-3">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                        <div className="tg-avatar">
                          {(() => {
                            const name = (draft.generation_params as any)?.channel_title || '';
                            const initials = name.split(' ').map((w:string) => w[0]).join('').slice(0,2).toUpperCase();
                            return initials || '•';
                          })()}
                        </div>
                        <span className="font-medium">{(draft.generation_params as any)?.channel_title || 'Original Post'}</span>
                        {draft.original_post_url && (
                          <a className="link ml-2" href={draft.original_post_url} target="_blank" rel="noreferrer">open</a>
                        )}
                        <span className="ml-auto">{new Date(draft.created_at).toLocaleString()}</span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{draft.original_post_content || draft.original_post_text_preview || '—'}</p>
                    </div>
                  )}

                  {/* Composer vs Posted bubble */}
                  {draft.status === 'POSTED' ? (
                    <div className="chat chat-end tg-draft-bubble tg-sent-bubble">
                      <div className="chat-bubble whitespace-pre-wrap max-w-full w-full">
                        {draft.final_text_to_post || draft.edited_text || draft.draft_text}
                      </div>
                      <div className="tg-sent-meta text-[11px] opacity-80">
                        <span className="badge badge-success">Posted</span>
                        {draft.original_post_url && (
                          <a className="tg-thread-link" href={draft.original_post_url} target="_blank" rel="noreferrer">Open thread</a>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="chat chat-start tg-draft-bubble">
                      <div className="relative chat-bubble bg-base-200 text-base-content whitespace-pre-wrap max-w-full w-full">
                        <textarea
                          className="w-full bg-transparent outline-none text-base leading-relaxed pr-24"
                          value={editingDrafts[draft.id] ?? draft.edited_text ?? draft.draft_text}
                          onChange={(e) => handleEditChange(draft.id, e.target.value)}
                          rows={5}
                        />
                        <button
                          className="absolute bottom-2 right-2 btn btn-sm bg-green-600 hover:bg-green-700"
                          onClick={() => handleSend(draft.id)}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Context buttons above text */}
                  <div className="mb-2 flex gap-2">
                    <button
                      className="btn btn-xs btn-outline"
                      onClick={() => setOpenBubbleKey(prev => prev === `chan:${draft.id}` ? null : `chan:${draft.id}`)}
                    >
                      Channel context
                    </button>
                    <button
                      className="btn btn-xs btn-outline"
                      onClick={() => setOpenBubbleKey(prev => prev === `msg:${draft.id}` ? null : `msg:${draft.id}`)}
                    >
                      Digital twin context
                    </button>
                  </div>

                  {/* Context bubbles: channel/topic + message context with edit capability */}
                  <div className="grid md:grid-cols-2">
                    <div className="relative">
                      {/* Popovers */}
                      <ContextBubble
                        id={`chan:${draft.id}`}
                        label="Channel context"
                        value={(draft.generation_params as any)?.channel_context ?? ''}
                        onChange={(v)=>handleEditChange(`${draft.id}::channel_context`, v)}
                        onSave={()=>handleSaveEdit(draft.id)}
                        isOpen={openBubbleKey === `chan:${draft.id}`}
                        onClose={()=>setOpenBubbleKey(null)}
                      />
                      <ContextBubble
                        id={`msg:${draft.id}`}
                        label="Digital twin context"
                        value={(draft.generation_params as any)?.message_context ?? ''}
                        onChange={(v)=>handleEditChange(`${draft.id}::message_context`, v)}
                        onSave={()=>handleSaveEdit(draft.id)}
                        isOpen={openBubbleKey === `msg:${draft.id}`}
                        onClose={()=>setOpenBubbleKey(null)}
                      />
                      {/* Style memory handled automatically; no UI */}
                    </div>
                  </div>

                  {draft.status !== 'POSTED' && (
                    <div className="mt-2 flex items-center gap-3 border-t border-white/10 pt-2">
                      <input
                        className="flex-1 px-3 py-2 border border-border rounded text-sm"
                        placeholder="Feedback to improve next draft (optional)"
                        value={regenFeedback[draft.id] ?? ''}
                        onChange={(e) => setRegenFeedback(prev => ({ ...prev, [draft.id]: e.target.value }))}
                      />
                      <div className="ml-auto flex items-center gap-2">
                        <Button size="sm" variant="outline" onClick={() => handleRegenerate(draft, post)}>Regenerate draft</Button>
                        {/* Send button moved inside textarea bubble */}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pagination - centered bottom controls */}
        <div className="mt-6 flex justify-center">
          <div className="join shadow-xl bg-base-200/60 backdrop-blur supports-[backdrop-filter]:bg-base-200/40 rounded-full p-1">
            <button
              className="join-item btn btn-ghost btn-sm"
              disabled={currentPage <= 1}
              onClick={() => fetchPosts('mock_init_data_for_telethon', Math.max(1, currentPage - 1), 30)}
            >
              ‹
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              // windowed pages around current
              const half = 2;
              let start = Math.max(1, currentPage - half);
              let end = Math.min(totalPages, start + 4);
              if (end - start < 4) start = Math.max(1, end - 4);
              const pageNum = start + i;
              return (
                <button
                  key={pageNum}
                  className={`join-item btn btn-sm ${pageNum === currentPage ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => fetchPosts('mock_init_data_for_telethon', pageNum, 30)}
                >
                  {pageNum}
                </button>
              );
            })}
            <button
              className="join-item btn btn-ghost btn-sm"
              disabled={currentPage >= totalPages}
              onClick={() => fetchPosts('mock_init_data_for_telethon', Math.min(totalPages, currentPage + 1), 30)}
            >
              ›
            </button>
          </div>
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



