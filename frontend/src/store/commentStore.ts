import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { ApiClient } from '@/core/api/api-client';
import { APIResponse } from '@/types/api';

// Draft Comment interface matching backend
export interface DraftComment {
  id: string;
  original_message_id: string;
  user_id: string;
  persona_name?: string;
  ai_model_used?: string;
  original_post_text_preview?: string;
  draft_text: string;
  edited_text?: string;
  final_text_to_post?: string;
  status: 'DRAFT' | 'EDITED' | 'APPROVED' | 'POSTED' | 'FAILED_TO_POST' | 'REJECTED';
  posted_telegram_message_id?: number;
  generation_params?: Record<string, any>;
  failure_reason?: string;
  created_at: string;
  updated_at: string;
}

// Legacy Comment interface for backward compatibility
export interface Comment {
  id: string;
  user_id: string;
  original_post_telegram_id: number;
  original_post_channel_telegram_id: number;
  draft_text: string;
  edited_text?: string;
  final_text_to_post?: string;
  status: 'DRAFT' | 'EDITED' | 'APPROVED' | 'POSTED' | 'FAILED_TO_POST' | 'REJECTED';
  ai_model_used?: string;
  generated_at: string;
  approved_at?: string;
  posted_at?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

interface CommentStore {
  // Draft comments (new AI system)
  drafts: DraftComment[];
  currentDraft: DraftComment | null;
  isGeneratingDraft: boolean;
  
  // Legacy comments (for backward compatibility)
  comments: Comment[];
  currentComment: Comment | null;
  isGenerating: boolean;
  isPosting: boolean;
  error: string | null;
  
  // Draft comment actions
  generateDraftComment: (postId: number, channelId: number, initDataRaw: string) => Promise<void>;
  fetchDrafts: (initDataRaw: string, status?: string) => Promise<void>;
  updateDraft: (draftId: string, editedText: string, initDataRaw: string, generationParams?: Record<string, any>) => Promise<void>;
  approveDraft: (draftId: string, initDataRaw: string) => Promise<void>;
  postDraft: (draftId: string, initDataRaw: string) => Promise<void>;
    regenerateDraft: (
      draftId: string,
      post: { id?: number; telegram_id?: number; original_message_id?: string; text?: string; channel_telegram_id?: number },
      rejectionReason: string | undefined,
      initDataRaw: string,
    ) => Promise<void>;
  setCurrentDraft: (draft: DraftComment | null) => void;
  
  // Legacy actions (for backward compatibility)
  generateComment: (postId: number, channelId: number, initDataRaw: string, userPrompt?: string) => Promise<void>;
  updateComment: (commentId: string, editedText: string, initDataRaw: string) => Promise<void>;
  approveComment: (commentId: string, initDataRaw: string) => Promise<void>;
  postComment: (commentId: string, initDataRaw: string) => Promise<void>;
  fetchComments: (postId?: number, status?: string, initDataRaw?: string) => Promise<void>;
  setCurrentComment: (comment: Comment | null) => void;
  
  // Common actions
  clearError: () => void;
  reset: () => void;
  // Realtime helper
  upsertDraft: (draft: DraftComment) => void;
}

// API client for draft comments
class DraftCommentAPI extends ApiClient {
  async generateDraft(postId: number, channelId: number, initDataRaw: string): Promise<APIResponse<{ status: string }>> {
    // Triggers background generation; draft arrives via WebSocket (new_ai_draft)
    return this.request<APIResponse<{ status: string }>>('/drafts/draft-comments/generate', {
      method: 'POST',
      body: JSON.stringify({
        post_telegram_id: postId,
        channel_telegram_id: channelId
      }),
    }, initDataRaw);
  }

  async getDrafts(initDataRaw: string, status?: string): Promise<APIResponse<DraftComment[]>> {
    const params = status ? `?status=${status}` : '';
    return this.request<APIResponse<DraftComment[]>>(`/drafts/draft-comments${params}`, {
      method: 'GET',
    }, initDataRaw);
  }

  async updateDraft(draftId: string, data: { edited_text?: string; status?: string; generation_params?: Record<string, any> }, initDataRaw: string): Promise<APIResponse<DraftComment>> {
    return this.request<APIResponse<DraftComment>>(`/drafts/draft-comments/${draftId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }, initDataRaw);
  }

  async approveDraft(draftId: string, initDataRaw: string): Promise<APIResponse<DraftComment>> {
    return this.request<APIResponse<DraftComment>>(`/drafts/draft-comments/${draftId}/approve`, {
      method: 'POST',
    }, initDataRaw);
  }

  async postDraft(draftId: string, initDataRaw: string): Promise<APIResponse<DraftComment>> {
    return this.request<APIResponse<DraftComment>>(`/drafts/draft-comments/${draftId}/post`, {
      method: 'POST',
    }, initDataRaw);
  }

  async regenerateDraft(
    draftId: string,
    postData: { original_message_id: string; original_post_url?: string; original_post_content?: string },
    rejectionReason: string | undefined,
    initDataRaw: string
  ): Promise<APIResponse<{ status: string }>> {
    return this.request<APIResponse<{ status: string }>>(`/drafts/draft-comments/${draftId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({
        post_data: postData,
        rejection_reason: rejectionReason,
      }),
    }, initDataRaw);
  }
}

const draftAPI = new DraftCommentAPI();

export const useCommentStore = create<CommentStore>()(
  subscribeWithSelector((set, get) => ({
    // Draft comments state
    drafts: [],
    currentDraft: null,
    isGeneratingDraft: false,
    
    // Legacy comments state
    comments: [],
    currentComment: null,
    isGenerating: false,
    isPosting: false,
    error: null,

    // Draft comment actions
    generateDraftComment: async (postId: number, channelId: number, initDataRaw: string) => {
      set({ isGeneratingDraft: true, error: null });
      
      try {
        const response = await draftAPI.generateDraft(postId, channelId, initDataRaw);
        if (!response.success) throw new Error(response.message || 'Failed to queue draft generation');
        // Stop spinner; draft will come via WS
        set({ isGeneratingDraft: false });
      } catch (error: any) {
        console.error('Error generating draft comment:', error);
        set({
          error: error.message || 'Failed to generate draft comment',
          isGeneratingDraft: false,
        });
      }
    },

    fetchDrafts: async (initDataRaw: string, status?: string) => {
      try {
        const response = await draftAPI.getDrafts(initDataRaw, status);
        
        if (response.success && response.data) {
          // Coalesce to latest per original_message_id to avoid stale items on UI
          const toTs = (d: DraftComment) => new Date(d.updated_at || d.created_at).getTime();
          const map = new Map<string, DraftComment>();
          for (const d of response.data) {
            const k = String(d.original_message_id);
            const prev = map.get(k);
            if (!prev || toTs(d) >= toTs(prev)) map.set(k, d);
          }
          set({ drafts: Array.from(map.values()) });
        }
      } catch (error: any) {
        console.error('Error fetching drafts:', error);
        set({ error: error.message || 'Failed to fetch drafts' });
      }
    },

    updateDraft: async (draftId: string, editedText: string, initDataRaw: string, generationParams?: Record<string, any>) => {
      try {
        const payload: any = { edited_text: editedText };
        if (generationParams) payload.generation_params = generationParams;
        const response = await draftAPI.updateDraft(draftId, payload, initDataRaw);
        
        if (response.success && response.data) {
          const updatedDraft: DraftComment = response.data;
          set(state => ({
            drafts: state.drafts.map(d => d.id === draftId ? updatedDraft : d),
            currentDraft: state.currentDraft?.id === draftId ? updatedDraft : state.currentDraft
          }));
        }
      } catch (error: any) {
        console.error('Error updating draft:', error);
        set({ error: error.message || 'Failed to update draft' });
      }
    },

    approveDraft: async (draftId: string, initDataRaw: string) => {
      try {
        const response = await draftAPI.approveDraft(draftId, initDataRaw);
        
        if (response.success && response.data) {
          const approvedDraft: DraftComment = response.data;
          set(state => ({
            drafts: state.drafts.map(d => d.id === draftId ? approvedDraft : d),
            currentDraft: state.currentDraft?.id === draftId ? approvedDraft : state.currentDraft
          }));
        }
      } catch (error: any) {
        console.error('Error approving draft:', error);
        set({ error: error.message || 'Failed to approve draft' });
      }
    },

    postDraft: async (draftId: string, initDataRaw: string) => {
      set({ isPosting: true, error: null });
      
      try {
        const response = await draftAPI.postDraft(draftId, initDataRaw);
        
        if (response.success && response.data) {
          const postedDraft: DraftComment = response.data;
          set(state => ({
            drafts: state.drafts.map(d => d.id === draftId ? postedDraft : d),
            currentDraft: state.currentDraft?.id === draftId ? postedDraft : state.currentDraft,
            isPosting: false
          }));
        } else {
          throw new Error(response.message || 'Failed to post draft');
        }
      } catch (error: any) {
        console.error('Error posting draft:', error);
        set({
          error: error.message || 'Failed to post draft',
          isPosting: false,
        });
      }
    },

    regenerateDraft: async (
      draftId: string,
      post: { id?: number; telegram_id?: number; original_message_id?: string; text?: string; channel_telegram_id?: number; },
      rejectionReason: string | undefined,
      initDataRaw: string,
    ) => {
      try {
        const originalId = post.original_message_id ?? (post.id != null ? String(post.id) : (post.telegram_id != null ? String(post.telegram_id) : ''));
        const regenStartedAt = Date.now();
        await draftAPI.regenerateDraft(
          draftId,
          {
            original_message_id: originalId,
            original_post_content: post.text,
          },
          rejectionReason,
          initDataRaw
        );
        // Poll a couple of times to allow the worker to create the new draft and WS to settle
        for (let i = 0; i < 12; i++) {
          try {
            await get().fetchDrafts(initDataRaw);
            // Check if a newer draft for this message id exists
            const latest = get().drafts
              .filter(d => String(d.original_message_id) === String(originalId))
              .sort((a,b)=> new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())[0];
            if (latest) {
              const ts = new Date(latest.updated_at || latest.created_at).getTime();
              if (ts >= regenStartedAt - 200) break;
            }
          } catch {}
          await new Promise(res => setTimeout(res, 500));
        }
      } catch (error: any) {
        console.error('Error regenerating draft:', error);
        set({ error: error.message || 'Failed to regenerate draft' });
      }
    },

    setCurrentDraft: (draft: DraftComment | null) => set({ currentDraft: draft }),

    // Legacy actions (for backward compatibility)
    generateComment: async (postId: number, channelId: number, initDataRaw: string, userPrompt?: string) => {
      // Redirect to new draft system
      return get().generateDraftComment(postId, channelId, initDataRaw);
    },

    updateComment: async (commentId: string, editedText: string, initDataRaw: string) => {
      try {
        // For backward compatibility, try to find in drafts first
        const draft = get().drafts.find(d => d.id === commentId);
        if (draft) {
          return get().updateDraft(commentId, editedText, initDataRaw);
        }

        // Legacy implementation
        const { currentComment } = get();
        if (currentComment && currentComment.id === commentId) {
          set({
            currentComment: {
              ...currentComment,
              edited_text: editedText,
              status: 'EDITED',
              updated_at: new Date().toISOString(),
            }
          });
        }
      } catch (error: any) {
        console.error('Error updating comment:', error);
        set({ error: error.message || 'Failed to update comment' });
      }
    },

    approveComment: async (commentId: string, initDataRaw: string) => {
      try {
        // For backward compatibility, try to find in drafts first
        const draft = get().drafts.find(d => d.id === commentId);
        if (draft) {
          return get().approveDraft(commentId, initDataRaw);
        }

        // Legacy implementation
        const { currentComment } = get();
        if (currentComment && currentComment.id === commentId) {
          set({
            currentComment: {
              ...currentComment,
              status: 'APPROVED',
              approved_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            }
          });
        }
      } catch (error: any) {
        console.error('Error approving comment:', error);
        set({ error: error.message || 'Failed to approve comment' });
      }
    },

    postComment: async (commentId: string, initDataRaw: string) => {
      // For backward compatibility, try to find in drafts first
      const draft = get().drafts.find(d => d.id === commentId);
      if (draft) {
        return get().postDraft(commentId, initDataRaw);
      }

      // Legacy implementation
      set({ isPosting: true, error: null });
      
      try {
        const { currentComment } = get();
        if (currentComment && currentComment.id === commentId) {
          set({
            currentComment: {
              ...currentComment,
              status: 'POSTED',
              posted_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            isPosting: false
          });
        }
      } catch (error: any) {
        console.error('Error posting comment:', error);
        set({
          error: error.message || 'Failed to post comment',
          isPosting: false,
        });
      }
    },

    fetchComments: async (postId?: number, status?: string, initDataRaw?: string) => {
      if (initDataRaw) {
        // Redirect to new draft system
        return get().fetchDrafts(initDataRaw, status);
      }
      
      try {
        // Legacy implementation
        console.log('Fetching legacy comments for post:', postId, 'status:', status);
      } catch (error: any) {
        console.error('Error fetching comments:', error);
        set({ error: error.message || 'Failed to fetch comments' });
      }
    },
    
    setCurrentComment: (comment: Comment | null) => {
      set({ currentComment: comment });
      
      // Also update currentDraft if it matches
      if (comment) {
        const draft = get().drafts.find(d => d.id === comment.id);
        if (draft) {
          set({ currentDraft: draft });
        }
      }
    },
    
    clearError: () => set({ error: null }),
    
    reset: () => set({
      drafts: [],
      currentDraft: null,
      isGeneratingDraft: false,
      comments: [],
      currentComment: null,
      isGenerating: false,
      isPosting: false,
      error: null,
    }),

    // Upsert helper used by WebSocket handler
    upsertDraft: (draft: DraftComment) => set((state) => {
      const exists = state.drafts.findIndex(d => d.id === draft.id);
      if (exists >= 0) {
        const copy = [...state.drafts];
        copy[exists] = draft;
        return { drafts: copy } as any;
      }
      return { drafts: [...state.drafts, draft] } as any;
    }),
  }))
); 