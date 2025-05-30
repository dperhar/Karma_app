'use client';

import { useState, useEffect } from 'react';
import { Post } from '@/core/api/services/post-service';
import { DraftComment, useCommentStore } from '@/store/commentStore';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CommentManagementPanelProps {
  selectedPost: Post | null;
  initDataRaw: string | null;
}

export const CommentManagementPanel: React.FC<CommentManagementPanelProps> = ({
  selectedPost,
  initDataRaw,
}) => {
  const { 
    drafts,
    currentDraft, 
    isGeneratingDraft, 
    isPosting, 
    error,
    generateDraftComment,
    fetchDrafts,
    updateDraft,
    approveDraft,
    postDraft,
    setCurrentDraft,
    clearError 
  } = useCommentStore();
  
  const [editedText, setEditedText] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // Загружаем черновики при инициализации
  useEffect(() => {
    if (initDataRaw) {
      fetchDrafts(initDataRaw);
    }
  }, [initDataRaw, fetchDrafts]);

  // Обновляем текущий черновик если выбран пост
  useEffect(() => {
    if (selectedPost && drafts.length > 0) {
      // Ищем черновик для выбранного поста
      const postDraft = drafts.find(draft => 
        draft.original_message_id === String(selectedPost.telegram_id)
      );
      if (postDraft) {
        setCurrentDraft(postDraft);
      } else {
        setCurrentDraft(null);
      }
    }
  }, [selectedPost, drafts, setCurrentDraft]);

  if (!selectedPost) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="text-muted-foreground mb-4">
          <svg className="w-16 h-16 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold mb-2">Select a post</h3>
        <p className="text-muted-foreground">
          Choose a post from the left panel to generate and manage AI comments.
        </p>
      </div>
    );
  }

  const handleGenerateComment = async () => {
    if (!initDataRaw) return;
    await generateDraftComment(selectedPost.telegram_id, selectedPost.channel_telegram_id, initDataRaw);
  };

  const handleStartEdit = () => {
    setEditedText(currentDraft?.edited_text || currentDraft?.draft_text || '');
    setIsEditing(true);
  };

  const handleSaveEdit = async () => {
    if (!currentDraft || !initDataRaw) return;
    
    await updateDraft(currentDraft.id, editedText, initDataRaw);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditedText('');
  };

  const handleApprove = async () => {
    if (!currentDraft || !initDataRaw) return;
    await approveDraft(currentDraft.id, initDataRaw);
  };

  const handlePost = async () => {
    if (!currentDraft || !initDataRaw) return;
    await postDraft(currentDraft.id, initDataRaw);
  };

  const getStatusColor = (status: DraftComment['status']) => {
    switch (status) {
      case 'DRAFT':
        return 'text-yellow-600 bg-yellow-100';
      case 'EDITED':
        return 'text-blue-600 bg-blue-100';
      case 'APPROVED':
        return 'text-green-600 bg-green-100';
      case 'POSTED':
        return 'text-green-800 bg-green-200';
      case 'FAILED_TO_POST':
        return 'text-red-600 bg-red-100';
      case 'REJECTED':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold">AI Comment Management</h2>
        <p className="text-sm text-muted-foreground">
          Channel: {selectedPost.channel.title}
        </p>
        {currentDraft?.persona_name && (
          <p className="text-xs text-muted-foreground">
            Persona: {currentDraft.persona_name}
          </p>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-100 border border-red-300 rounded-md">
          <div className="flex justify-between items-start">
            <p className="text-red-700 text-sm">{error}</p>
            <button
              onClick={clearError}
              className="text-red-500 hover:text-red-700"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isGeneratingDraft ? (
          <div className="flex flex-col items-center justify-center h-full">
            <svg className="animate-spin h-8 w-8 text-primary mb-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-muted-foreground">Generating AI comment...</p>
          </div>
        ) : currentDraft ? (
          <div className="space-y-4">
            {/* Post preview */}
            <div className="p-3 bg-gray-50 rounded-md border-l-4 border-blue-500">
              <h4 className="text-sm font-medium mb-2">Original Post:</h4>
              <p className="text-sm text-gray-700">
                {selectedPost.text.length > 200 
                  ? selectedPost.text.substring(0, 200) + '...'
                  : selectedPost.text
                }
              </p>
            </div>

            {/* Status and model info */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn(
                "px-2 py-1 rounded-full text-xs font-medium",
                getStatusColor(currentDraft.status)
              )}>
                {currentDraft.status}
              </span>
              {currentDraft.ai_model_used && (
                <span className="text-xs text-muted-foreground bg-gray-100 px-2 py-1 rounded">
                  {currentDraft.ai_model_used}
                </span>
              )}
              {currentDraft.persona_name && (
                <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                  {currentDraft.persona_name}
                </span>
              )}
            </div>

            {/* Comment text */}
            <div className="space-y-2">
              <label className="text-sm font-medium">AI Generated Comment:</label>
              {isEditing ? (
                <div className="space-y-2">
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full h-32 p-3 border border-border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="Edit your comment..."
                  />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={handleSaveEdit}>
                      Save Changes
                    </Button>
                    <Button size="sm" variant="outline" onClick={handleCancelEdit}>
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="p-3 bg-muted rounded-md">
                  <p className="text-sm whitespace-pre-wrap">
                    {currentDraft.edited_text || currentDraft.draft_text}
                  </p>
                  {currentDraft.status !== 'POSTED' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="mt-2"
                      onClick={handleStartEdit}
                    >
                      Edit Comment
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* Action buttons */}
            {!isEditing && (
              <div className="flex gap-2 pt-4 border-t">
                {(currentDraft.status === 'DRAFT' || currentDraft.status === 'EDITED') && (
                  <Button onClick={handleApprove} disabled={isPosting}>
                    Approve Comment
                  </Button>
                )}
                
                {currentDraft.status === 'APPROVED' && (
                  <Button onClick={handlePost} disabled={isPosting} className="bg-green-600 hover:bg-green-700">
                    {isPosting ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Posting...
                      </>
                    ) : (
                      'Post to Telegram'
                    )}
                  </Button>
                )}

                {currentDraft.status === 'POSTED' && (
                  <div className="flex items-center gap-2 text-green-600">
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span className="font-medium">Posted successfully!</span>
                    {currentDraft.posted_telegram_message_id && (
                      <span className="text-xs text-gray-500">
                        (ID: {currentDraft.posted_telegram_message_id})
                      </span>
                    )}
                  </div>
                )}

                {currentDraft.status === 'FAILED_TO_POST' && currentDraft.failure_reason && (
                  <div className="text-red-600 text-sm">
                    <strong>Failed to post:</strong> {currentDraft.failure_reason}
                  </div>
                )}
              </div>
            )}

            {/* Metadata */}
            <div className="pt-4 border-t border-border text-xs text-muted-foreground space-y-1">
              <p>Generated: {new Date(currentDraft.created_at).toLocaleString()}</p>
              <p>Last updated: {new Date(currentDraft.updated_at).toLocaleString()}</p>
              {currentDraft.generation_params && (
                <details className="mt-2">
                  <summary className="cursor-pointer text-blue-600">Generation Details</summary>
                  <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-auto">
                    {JSON.stringify(currentDraft.generation_params, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-muted-foreground mb-4">
              <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">Generate AI Comment</h3>
            <p className="text-muted-foreground mb-4">
              No AI comment found for this post. Generate one using your configured persona.
            </p>
            <Button onClick={handleGenerateComment} disabled={!initDataRaw} className="bg-blue-600 hover:bg-blue-700">
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              Generate Comment
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}; 