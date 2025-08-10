'use client';

import { useState, useEffect } from 'react';
// import { initData, useSignal } from '@telegram-apps/sdk-react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { Page } from '@/components/Page';
import { Header } from '@/components/Header';
import { Preloader } from '@/components/Preloader/Preloader';
import { CommentManagementPanel } from '@/components/CommentManagementPanel/CommentManagementPanel';
import { DraftList } from '@/components/CommentManagementPanel/DraftList';
import { PersonaSettings } from '@/components/PersonaSettings/PersonaSettings';
import { Button } from '@/components/ui/button';
import { useCommentStore } from '@/store/commentStore';
import { useUserStore } from '@/store/userStore';
import { usePostStore } from '@/store/postStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Post } from '@/core/api/services/post-service';

type ViewMode = 'drafts' | 'posts' | 'persona';

export default function AIComments() {
  const t = useTranslations('i18n');
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<ViewMode>('drafts');
  const [selectedPost, setSelectedPost] = useState<Post | null>(null);
  
  // Get the Telegram initialization data
  // const initDataRaw = useSignal(initData.raw);
  // const initDataState = useSignal(initData.state);
  
  const { user, fetchUser, isLoading: userLoading, error: userError } = useUserStore();
  const { posts, fetchPosts } = usePostStore();
  const { drafts, fetchDrafts } = useCommentStore();
  
  // WebSocket connection for real-time updates
  const { isConnected: wsConnected, error: wsError } = useWebSocket({
    userId: user?.id,
    // initDataRaw
  });

  // Load initial data
  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        // Use mock initDataRaw for Telethon since backend still expects it
        const mockInitDataRaw = "mock_init_data_for_telethon";
        
        // Fetch fresh user data from server first
        await fetchUser(mockInitDataRaw);
        
        // Load drafts
        await fetchDrafts(mockInitDataRaw);
        
        // Load recent posts for reference
        await fetchPosts(mockInitDataRaw, 1, 20);
      } catch (err) {
        console.error('Failed to load AI comments data:', err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    // Check if user is authenticated via session (since we use Telethon, not SDK)
    const isSessionAuthenticated = typeof window !== 'undefined' && 
      sessionStorage.getItem("env-authenticated") === "1";
    
    // Only proceed with data loading if user is authenticated
    if (isSessionAuthenticated) {
      console.log('[AIComments] Starting data load - user authenticated via session...');
      loadData();
    } else {
      console.log('[AIComments] Not loading data - user not authenticated');
    }
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [fetchUser, fetchDrafts, fetchPosts]);

  const handleBackClick = () => {
    router.push('/');
  };

  const handlePostSelect = (post: Post) => {
    setSelectedPost(post);
    if (viewMode !== 'posts') {
      setViewMode('posts');
    }
  };

  if (loading) {
    return (
      <Page back={true} onBack={handleBackClick}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }

  return (
    <Page back={true} onBack={handleBackClick}>
      <Header 
        title="AI Comment Management"
        onSettingsClick={() => setViewMode('persona')}
      />
      
      <div className="flex flex-col h-screen bg-background">
        {/* Navigation */}
        <div className="border-b border-border bg-white">
          <div className="flex items-center justify-between p-4">
            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === 'drafts' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('drafts')}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Drafts ({drafts.length})
              </Button>
              <Button
                variant={viewMode === 'posts' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('posts')}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
                Posts
              </Button>
              <Button
                variant={viewMode === 'persona' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('persona')}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                Persona
              </Button>
            </div>
            
            {/* Connection status */}
            <div className="flex items-center gap-2">
              {wsConnected ? (
                <div className="flex items-center gap-1 text-green-600 text-xs">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  Real-time
                </div>
              ) : (
                <div className="flex items-center gap-1 text-gray-500 text-xs">
                  <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                  Offline
                </div>
              )}
              
              {(user as any)?.persona_name && (
                <div className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                  {(user as any).persona_name}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {viewMode === 'drafts' && (
            <div className="flex w-full">
              {/* Drafts list */}
              <div className="w-1/3 border-r border-border">
                <DraftList 
                  // initDataRaw={initDataRaw || null}
                  onSelectDraft={(draft) => {
                    // Find the post for this draft if available
                    const post = posts.find(p => p.telegram_id.toString() === draft.original_message_id);
                    if (post) {
                      setSelectedPost(post);
                    }
                  }}
                />
              </div>
              
              {/* Draft management */}
              <div className="flex-1">
                <CommentManagementPanel
                  selectedPost={selectedPost}
                  // initDataRaw={initDataRaw || null}
                />
              </div>
            </div>
          )}

          {viewMode === 'posts' && (
            <div className="flex w-full">
              {/* Posts list */}
              <div className="w-1/3 border-r border-border overflow-y-auto">
                <div className="p-4 border-b border-border">
                  <h3 className="text-lg font-semibold">Recent Posts</h3>
                  <p className="text-sm text-muted-foreground">
                    Select a post to manage AI comments
                  </p>
                </div>
                
                <div className="space-y-2 p-2">
                  {posts.map((post) => {
                    const hasDraft = drafts.some(d => d.original_message_id === post.telegram_id.toString());
                    
                    return (
                      <div
                        key={post.id}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${
                          selectedPost?.id === post.id ? 'border-primary bg-primary/5' : 'border-border'
                        }`}
                        onClick={() => handlePostSelect(post)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                            {post.channel.title}
                          </span>
                          {hasDraft && (
                            <span className="text-xs text-green-600 bg-green-100 px-2 py-1 rounded">
                              Has Draft
                            </span>
                          )}
                        </div>
                        
                        <p className="text-sm line-clamp-3">
                          {post.text}
                        </p>
                        
                        <div className="mt-2 text-xs text-muted-foreground">
                          {new Date(post.date).toLocaleDateString('ru-RU', {
                            day: '2-digit',
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              
              {/* Comment management */}
              <div className="flex-1">
                <CommentManagementPanel
                  selectedPost={selectedPost}
                  // initDataRaw={initDataRaw || null}
                />
              </div>
            </div>
          )}

          {viewMode === 'persona' && (
            <div className="w-full overflow-y-auto">
              <PersonaSettings
                // initDataRaw={initDataRaw || null}
              />
            </div>
          )}
        </div>

        {/* Bottom status bar */}
        <div className="border-t border-border bg-white p-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>Total drafts: {drafts.length}</span>
              <span>Published: {drafts.filter(d => d.status === 'POSTED').length}</span>
              <span>Pending: {drafts.filter(d => d.status === 'APPROVED').length}</span>
            </div>
            
            {wsError && (
              <div className="text-red-600">
                WebSocket error: {wsError}
              </div>
            )}
          </div>
        </div>
      </div>
    </Page>
  );
} 