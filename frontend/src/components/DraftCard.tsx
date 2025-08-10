'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { DraftComment } from '@/store/commentStore';
import { Post } from '@/core/api/services/post-service';
import ContextBubble from './ContextBubble';

export interface DraftCardProps {
  post?: Post;
  draft: DraftComment;
  editingText: string | undefined;
  feedback: string | undefined;
  openBubbleKey: string | null;
  onChangeText: (text: string) => void;
  onSend: () => void;
  onRegenerate: () => void;
  onToggleChannelCtx: () => void;
  onToggleMsgCtx: () => void;
  onCtxChange: (fieldKey: string, value: string) => void;
  onCtxSave: () => void;
  onCtxClose: () => void;
}

export function DraftCard(props: DraftCardProps) {
  const {
    post,
    draft,
    editingText,
    feedback,
    openBubbleKey,
    onChangeText,
    onSend,
    onRegenerate,
    onToggleChannelCtx,
    onToggleMsgCtx,
    onCtxChange,
    onCtxSave,
    onCtxClose,
  } = props;

  return (
    <div className="card tg-post">
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
                    const initials = name
                      .split(' ')
                      .map((w) => w[0])
                      .join('')
                      .slice(0, 2)
                      .toUpperCase();
                    return initials || '•';
                  })()
                )}
              </div>
              <span className="tg-post-title">{post.channel.title}</span>
              <span>·</span>
              <span>{new Date(post.date).toLocaleString()}</span>
              {typeof post.replies === 'number' && <span className="ml-auto">Replies: {post.replies}</span>}
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
                  const initials = name
                    .split(' ')
                    .map((w: string) => w[0])
                    .join('')
                    .slice(0, 2)
                    .toUpperCase();
                  return initials || '•';
                })()}
              </div>
              <span className="font-medium">{(draft.generation_params as any)?.channel_title || 'Original Post'}</span>
              {draft.original_post_url && (
                <a className="link ml-2" href={draft.original_post_url} target="_blank" rel="noreferrer">
                  open
                </a>
              )}
              <span className="ml-auto">{new Date(draft.created_at).toLocaleString()}</span>
            </div>
            <p className="text-sm whitespace-pre-wrap">
              {draft.original_post_content || draft.original_post_text_preview || '—'}
            </p>
          </div>
        )}

        {draft.status === 'POSTED' ? (
          <div className="chat chat-end tg-draft-bubble tg-sent-bubble">
            <div className="chat-bubble whitespace-pre-wrap max-w-full w-full">
              {draft.final_text_to_post || draft.edited_text || draft.draft_text}
            </div>
            <div className="tg-sent-meta text-[11px] opacity-80">
              <span className="badge badge-success">Posted</span>
              {draft.original_post_url && (
                <a className="tg-thread-link" href={draft.original_post_url} target="_blank" rel="noreferrer">
                  Open thread
                </a>
              )}
            </div>
          </div>
        ) : (
          <div className="chat chat-start tg-draft-bubble">
            <div className="relative chat-bubble bg-base-200 text-base-content whitespace-pre-wrap max-w-full w-full">
              <textarea
                className="w-full bg-transparent outline-none text-base leading-relaxed pr-24"
                value={editingText ?? draft.edited_text ?? draft.draft_text}
                onChange={(e) => onChangeText(e.target.value)}
                rows={5}
              />
              <button className="absolute bottom-2 right-2 btn btn-sm bg-green-600 hover:bg-green-700" onClick={onSend}>
                Send
              </button>
            </div>
          </div>
        )}

        <div className="mb-2 flex gap-2">
          <button className="btn btn-xs btn-outline" onClick={onToggleChannelCtx}>
            Channel context
          </button>
          <button className="btn btn-xs btn-outline" onClick={onToggleMsgCtx}>
            Digital twin context
          </button>
        </div>

        <div className="grid md:grid-cols-2">
          <div className="relative">
            <ContextBubble
              id={`chan:${draft.id}`}
              label="Channel context"
              value={(draft.generation_params as any)?.channel_context ?? ''}
              onChange={(v) => onCtxChange(`${draft.id}::channel_context`, v)}
              onSave={onCtxSave}
              isOpen={openBubbleKey === `chan:${draft.id}`}
              onClose={onCtxClose}
            />
            <ContextBubble
              id={`msg:${draft.id}`}
              label="Digital twin context"
              value={(draft.generation_params as any)?.message_context ?? ''}
              onChange={(v) => onCtxChange(`${draft.id}::message_context`, v)}
              onSave={onCtxSave}
              isOpen={openBubbleKey === `msg:${draft.id}`}
              onClose={onCtxClose}
            />
          </div>
        </div>

        {draft.status !== 'POSTED' && (
          <div className="mt-2 flex items-center gap-3 border-t border-white/10 pt-2">
            <input
              className="flex-1 px-3 py-2 border border-border rounded text-sm"
              placeholder="Feedback to improve next draft (optional)"
              value={feedback ?? ''}
              onChange={(e) => onCtxChange(`fb:${draft.id}`, e.target.value)}
            />
            <div className="ml-auto flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={onRegenerate}>
                Regenerate draft
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DraftCard;


