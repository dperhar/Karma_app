'use client';

import React from 'react';

export interface PagerProps {
  currentPage: number;
  totalPages: number;
  onPage: (page: number) => void;
}

export function Pager({ currentPage, totalPages, onPage }: PagerProps) {
  const maxButtons = 5;
  const half = 2;
  let start = Math.max(1, currentPage - half);
  let end = Math.min(totalPages, start + (maxButtons - 1));
  if (end - start < maxButtons - 1) start = Math.max(1, end - (maxButtons - 1));

  const pages = [] as number[];
  for (let p = start; p <= end; p++) pages.push(p);

  return (
    <div className="mt-6 flex justify-center">
      <div className="join shadow-xl bg-base-200/60 backdrop-blur supports-[backdrop-filter]:bg-base-200/40 rounded-full p-1">
        <button
          className="join-item btn btn-ghost btn-sm"
          disabled={currentPage <= 1}
          onClick={() => onPage(Math.max(1, currentPage - 1))}
        >
          ‹
        </button>
        {pages.map((page) => (
          <button
            key={page}
            className={`join-item btn btn-sm ${page === currentPage ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => onPage(page)}
          >
            {page}
          </button>
        ))}
        <button
          className="join-item btn btn-ghost btn-sm"
          disabled={currentPage >= totalPages}
          onClick={() => onPage(Math.min(totalPages, currentPage + 1))}
        >
          ›
        </button>
      </div>
    </div>
  );
}

export default Pager;


