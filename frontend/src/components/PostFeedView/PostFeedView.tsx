'use client';

import { Post } from '@/core/api/services/post-service';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface PostFeedViewProps {
  posts: Post[];
  selectedPost: Post | null;
  onPostSelect: (post: Post) => void;
  onGenerateComment: (post: Post) => void;
  isGenerating: boolean;
}

export const PostFeedView: React.FC<PostFeedViewProps> = ({
  posts,
  selectedPost,
  onPostSelect,
  onGenerateComment,
  isGenerating,
}) => {
  if (posts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="text-muted-foreground mb-4">
          <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold mb-2">No posts found</h3>
        <p className="text-muted-foreground">
          Connect your Telegram account to see posts from your channels and chats.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">Recent Posts</h2>
        <p className="text-sm text-muted-foreground">
          {posts.length} posts from your channels and chats
        </p>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {posts.map((post) => (
          <PostItem
            key={`${post.channel_telegram_id}-${post.telegram_id}`}
            post={post}
            isSelected={selectedPost?.telegram_id === post.telegram_id}
            onSelect={() => onPostSelect(post)}
            onGenerateComment={() => onGenerateComment(post)}
            isGenerating={isGenerating}
          />
        ))}
      </div>
    </div>
  );
};

interface PostItemProps {
  post: Post;
  isSelected: boolean;
  onSelect: () => void;
  onGenerateComment: () => void;
  isGenerating: boolean;
}

const PostItem: React.FC<PostItemProps> = ({
  post,
  isSelected,
  onSelect,
  onGenerateComment,
  isGenerating,
}) => {
  const formatDate = (dateString: string) => {
    try {
      return formatDistanceToNow(new Date(dateString), { addSuffix: true });
    } catch {
      return 'Unknown time';
    }
  };

  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'channel':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        );
      case 'chat':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div
      className={cn(
        "p-4 border-b border-border cursor-pointer transition-colors hover:bg-accent/50",
        isSelected && "bg-accent border-l-4 border-l-primary"
      )}
      onClick={onSelect}
    >
      {/* Channel info */}
      <div className="flex items-center gap-2 mb-2">
        <div className="text-muted-foreground">
          {getChannelIcon(post.channel.type)}
        </div>
        <span className="font-medium text-sm">{post.channel.title}</span>
        {post.channel.username && (
          <span className="text-xs text-muted-foreground">@{post.channel.username}</span>
        )}
        <span className="text-xs text-muted-foreground ml-auto">
          {formatDate(post.date)}
        </span>
      </div>

      {/* Post content */}
      <div className="mb-3">
        <p className="text-sm line-clamp-3 text-foreground">
          {post.text || 'Media post'}
        </p>
        {post.media_type && (
          <div className="mt-2 text-xs text-muted-foreground flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
            </svg>
            {post.media_type}
          </div>
        )}
      </div>

      {/* Post stats */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
        {post.views && (
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
            </svg>
            {post.views.toLocaleString()}
          </span>
        )}
        {post.reactions.length > 0 && (
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
            </svg>
            {post.reactions.reduce((sum, r) => sum + r.count, 0)}
          </span>
        )}
        {post.replies && (
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7z" clipRule="evenodd" />
            </svg>
            {post.replies}
          </span>
        )}
      </div>

      {/* Generate comment button */}
      <div className="flex justify-end">
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            onGenerateComment();
          }}
          disabled={isGenerating}
        >
          {isGenerating ? (
            <>
              <svg className="animate-spin -ml-1 mr-2 h-3 w-3" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </>
          ) : (
            'Generate Comment'
          )}
        </Button>
      </div>
    </div>
  );
}; 