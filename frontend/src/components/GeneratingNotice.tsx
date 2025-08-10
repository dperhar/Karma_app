'use client';

import React from 'react';

export default function GeneratingNotice() {
  return (
    <div className="w-full flex justify-center mb-3">
      <div className="flex items-center gap-3 px-4 py-2 rounded-full border border-white/10 bg-base-200/60 backdrop-blur supports-[backdrop-filter]:bg-base-200/40 shadow-lg">
        <span className="loading loading-spinner loading-xs text-primary" />
        <span className="text-sm opacity-90">AI drafts are being prepared for these posts. Hang tight…</span>
      </div>
    </div>
  );
}


