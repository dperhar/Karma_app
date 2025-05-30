'use client';

import { initData, useSignal } from '@telegram-apps/sdk-react';
import { useEffect, useState } from 'react';
import { Header } from '@/components/Header';
import { Page } from '@/components/Page';
import { Preloader } from '@/components/Preloader/Preloader';
import { PostFeedView } from '@/components/PostFeedView/PostFeedView';
import { CommentManagementPanel } from '@/components/CommentManagementPanel/CommentManagementPanel';
import { useUserStore } from '@/store/userStore';
import { usePostStore } from '@/store/postStore';
import { useCommentStore } from '@/store/commentStore';

export default function CommentsPage() {
  const [loading, setLoading] = useState(true);
  const [selectedPost, setSelectedPost] = useState<any>(null);
  
  // Get the Telegram initialization data
  const initDataRaw = useSignal(initData.raw);
  const initDataState = useSignal(initData.state);
  
  const { user, fetchUser, isLoading: userLoading, error: userError } = useUserStore();
  const { posts, fetchPosts, isLoading: postsLoading, error: postsError } = usePostStore();
  const { generateComment, isGenerating } = useCommentStore();

  // Initial data loading
  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        console.log('Loading comment management data...');
        
        // Check if we have valid initialization data
        if (!initDataRaw) {
          console.error('No Telegram init data available');
          return;
        }
        
        // Fetch user data first
        await fetchUser(initDataRaw);
        
        // Fetch posts from user's channels/chats
        await fetchPosts(initDataRaw);
        
      } catch (err) {
        console.error('Failed to load data:', err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    // Only proceed with data loading if initialization data is available
    if (initDataState && initDataRaw) {
      loadData();
    }
    
    // Cleanup function
    return () => {
      isMounted = false;
    };
  }, [fetchUser, fetchPosts, initDataRaw, initDataState]);

  const handlePostSelect = (post: any) => {
    setSelectedPost(post);
  };

  const handleGenerateComment = async (post: any) => {
    if (!initDataRaw) return;
    
    try {
      await generateComment(post.telegram_id, post.channel_telegram_id, initDataRaw);
    } catch (error) {
      console.error('Failed to generate comment:', error);
    }
  };

  if (loading || userLoading || postsLoading) {
    return (
      <Page back={false}>
        <div className="flex justify-center items-center min-h-screen">
          <Preloader />
        </div>
      </Page>
    );
  }

  if (userError || postsError) {
    return (
      <Page back={false}>
        <div className="alert alert-error shadow-lg mx-4 my-6">
          <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current flex-shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="font-bold">Error</h3>
            <div className="text-sm">{userError || postsError}</div>
          </div>
        </div>
      </Page>
    );
  }

  return (
    <Page back={false}>
      <Header 
        title="Comment Management"
        onSettingsClick={() => {/* Navigate to settings */}}
      />
      
      {/* Two-column layout */}
      <div className="flex h-[calc(100vh-4rem)] bg-background">
        {/* Left column - Posts feed */}
        <div className="w-1/2 border-r border-border overflow-hidden">
          <PostFeedView
            posts={posts}
            selectedPost={selectedPost}
            onPostSelect={handlePostSelect}
            onGenerateComment={handleGenerateComment}
            isGenerating={isGenerating}
          />
        </div>
        
        {/* Right column - Comment management */}
        <div className="w-1/2 overflow-hidden">
          <CommentManagementPanel
            selectedPost={selectedPost}
            initDataRaw={initDataRaw || null}
          />
        </div>
      </div>
    </Page>
  );
} 