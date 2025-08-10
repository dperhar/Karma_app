'use client';

import React from 'react';

export interface ContextBubbleProps {
  id: string;
  label: string;
  value: string;
  isOpen: boolean;
  onChange: (v: string) => void;
  onSave: () => void;
  onClose: () => void;
}

export function ContextBubble(props: ContextBubbleProps) {
  const { id, label, value, isOpen, onChange, onSave, onClose } = props;
  if (!isOpen) return null;
  return (
    <div className="absolute bottom-full left-0 mb-2 z-50" data-id={id}>
      <div
        className="rounded-xl shadow-xl border border-border bg-base-100 p-3"
        style={{ minWidth: '10rem', minHeight: '5rem', maxWidth: '25vw', maxHeight: '25vh' }}
      >
        <div className="flex items-center mb-2 text-xs opacity-70">
          <span className="font-medium mr-2">{label}</span>
          <button className="ml-auto btn btn-ghost btn-xs" onClick={onClose}>
            ✕
          </button>
        </div>
        <textarea
          className="w-full bg-transparent outline-none text-sm resize-none overflow-auto"
          style={{ maxHeight: '20vh' }}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={5}
        />
        <div className="mt-2 text-right">
          <button className="btn btn-xs btn-primary" onClick={onSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default ContextBubble;


