'use client';

import React from 'react';

export function GeneratingNotice() {
  return (
    <div className="w-full flex justify-center">
      <div className="inline-flex items-center gap-3 px-4 py-2 rounded-full bg-base-200/60 border border-white/10 shadow-lg">
        <span className="loading loading-spinner loading-sm text-primary" />
        <span className="text-sm opacity-80">AI is generating drafts for this page…</span>
      </div>
    </div>
  );
}

export default GeneratingNotice;


