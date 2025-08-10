import { create } from 'zustand';
import { postService, Post } from '@/core/api/services/post-service';

interface PostStore {
  posts: Post[];
  isLoading: boolean;
  error: string | null;
  currentPage: number;
  totalPages: number;
  
  fetchPosts: (initDataRaw: string, page?: number, limit?: number) => Promise<void>;
  fetchPost: (postId: number, channelId: number, initDataRaw: string) => Promise<Post | null>;
  clearError: () => void;
  reset: () => void;
}

export const usePostStore = create<PostStore>((set, get) => ({
  posts: [],
  isLoading: false,
  error: null,
  currentPage: 1,
  totalPages: 1,

  fetchPosts: async (initDataRaw: string, page = 1, limit = 20) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await postService.getPosts(initDataRaw, page, limit);

      if (response.success && response.data) {
        set({
          posts: response.data.posts,
          currentPage: response.data.page,
          totalPages: Math.ceil(response.data.total / response.data.limit),
          isLoading: false,
        });
      } else {
        set({
          error: 'Failed to fetch posts',
          isLoading: false,
        });
      }
    } catch (error: any) {
      console.error('Error fetching posts:', error);
      set({
        error: error.message || 'Failed to fetch posts',
        isLoading: false,
      });
    }
  },

  fetchPost: async (postId: number, channelId: number, initDataRaw: string) => {
    try {
      const response = await postService.getPost(postId, channelId, initDataRaw);

      if (response.success && response.data) {
        return response.data;
      }
      return null;
    } catch (error: any) {
      console.error('Error fetching post:', error);
      return null;
    }
  },

  clearError: () => set({ error: null }),
  
  reset: () => set({
    posts: [],
    isLoading: false,
    error: null,
    currentPage: 1,
    totalPages: 1,
  }),
})); 