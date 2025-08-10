import { APIResponse } from '@/types/api';
import { ApiClient } from '../api-client';

export interface Post {
  id: number;
  telegram_id: number;
  channel_telegram_id: number;
  channel: {
    id: number;
    title: string;
    username?: string;
    type: 'channel' | 'chat';
  };
  text: string;
  date: string;
  views?: number;
  forwards?: number;
  replies?: number;
  reactions?: Array<{
    reaction: any;
    count: number;
    chosen: boolean;
    emoticon?: string;
    custom_emoji_id?: string;
  }>;
  media_type?: string;
  media_url?: string;
  is_pinned: boolean;
  sender_id?: number;
  reply_to_msg_id?: number;
  created_at: string;
  updated_at: string;
}

interface PostsResponse {
  posts: Post[];
  total: number;
  page: number;
  limit: number;
}

export class PostService extends ApiClient {
  private readonly endpoint = '/feed';

  constructor() {
    super();
    console.log('PostService initialized with endpoint:', this.endpoint);
  }

  async getPosts(
    initDataRaw: string,
    page: number = 1,
    limit: number = 50,
    source: 'channel' | 'supergroup' | 'combined' = 'channel'
  ): Promise<APIResponse<PostsResponse>> {
    console.log('getPosts called with page:', page, 'limit:', limit);
    try {
      const response = await this.request<APIResponse<PostsResponse>>(
        `${this.endpoint}?page=${page}&limit=${limit}&source=${source}`,
        {
          method: 'GET',
        },
        initDataRaw
      );
      
      console.log('getPosts response:', response);
      return response;
    } catch (error) {
      console.error('Failed to get posts:', error);
      throw error;
    }
  }

  async getPost(
    postId: number,
    channelId: number,
    initDataRaw: string
  ): Promise<APIResponse<Post>> {
    console.log('getPost called for post:', postId, 'channel:', channelId);
    try {
      const response = await this.request<APIResponse<Post>>(
        `${this.endpoint}/${postId}?channel_id=${channelId}`,
        {
          method: 'GET',
        },
        initDataRaw
      );
      
      console.log('getPost response:', response);
      return response;
    } catch (error) {
      console.error('Failed to get post:', error);
      throw error;
    }
  }
}

export const postService = new PostService(); 