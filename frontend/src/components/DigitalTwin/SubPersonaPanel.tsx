'use client';

import React, { useMemo, useState, useEffect, useRef } from 'react';

export interface SubPersonaPanelProps {
  personas: Record<string, any>;
  onChange: (next: Record<string, any>) => void;
  onPreview: (text: string) => Promise<{ persona: string | null; full_scores?: Record<string, { score: number }> } | null>;
}

const Chip: React.FC<{ active?: boolean; onClick?: () => void; label: string; score?: number }> = ({ active, onClick, label, score }) => (
  <button className={`btn btn-xs ${active ? 'btn-primary' : 'btn-ghost'}`} onClick={onClick}>
    {label}{typeof score === 'number' ? ` · ${score.toFixed(2)}` : ''}
  </button>
);

export const SubPersonaPanel: React.FC<SubPersonaPanelProps> = ({ personas, onChange, onPreview }) => {
  const names = useMemo(() => Object.keys(personas || {}), [personas]);
  const [selected, setSelected] = useState<string | null>(names[0] || null);
  const [preview, setPreview] = useState('');
  const [scores, setScores] = useState<Record<string, number>>({});

  const p = (selected && personas[selected]) || {};

  const semanticRef = useRef<HTMLTextAreaElement | null>(null);
  const examplesRef = useRef<HTMLTextAreaElement | null>(null);
  const triggersRef = useRef<HTMLTextAreaElement | null>(null);
  const previewRef = useRef<HTMLTextAreaElement | null>(null);

  const update = (path: string[], value: any) => {
    const next = JSON.parse(JSON.stringify(personas||{}));
    let cur:any = next;
    for (let i=0;i<path.length-1;i++){ const k = path[i]; cur[k] = cur[k]||{}; cur = cur[k]; }
    cur[path[path.length-1]] = value;
    onChange(next);
  };

  const autoResize = (el: HTMLTextAreaElement) => {
    if (!el) return;
    el.style.height = '0px';
    const next = Math.min(el.scrollHeight, 320); // cap to avoid runaway
    el.style.height = next + 'px';
  };

  const addPersona = (name: string) => {
    if (!name) return;
    const next = { ...(personas||{}) } as Record<string, any>;
    if (!next[name]) next[name] = { triggers: [], semantic_hints: [], examples: [] };
    onChange(next);
    setSelected(name);
  };

  useEffect(() => {
    const auto = (el: HTMLTextAreaElement | null) => {
      if (!el) return;
      el.style.height = '0px';
      el.style.height = Math.min(el.scrollHeight, 480) + 'px';
    };
    auto(semanticRef.current);
    auto(examplesRef.current);
    auto(triggersRef.current);
  }, [selected, p.semantic_hints, p.examples, p.triggers]);

  useEffect(() => {
    if (!previewRef.current) return;
    previewRef.current.style.height = '0px';
    previewRef.current.style.height = Math.min(previewRef.current.scrollHeight, 600) + 'px';
  }, [preview]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      {/* Left rail */}
      <div className="md:col-span-1 flex flex-col gap-2">
        <div className="label text-sm opacity-70">Sub‑personas</div>
        <div className="flex flex-wrap gap-2">
          {names.map(n => (
            <Chip key={n} label={n} onClick={()=>setSelected(n)} active={selected===n} score={scores[n]} />
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input className="input input-bordered input-sm flex-1" placeholder="Add sub‑persona" onKeyDown={(e:any)=>{ if(e.key==='Enter'){ addPersona((e.target.value||'').trim()); e.target.value=''; } }} />
          <button className="btn btn-sm whitespace-nowrap" onClick={()=>{ const v=(document.activeElement as HTMLInputElement)?.value?.trim(); if(v){ addPersona(v); (document.activeElement as HTMLInputElement).value=''; } }}>Добавить</button>
        </div>
      </div>

      {/* Editor */}
      <div className="md:col-span-3 card bg-base-200">
        <div className="card-body gap-3">
          {selected ? (
            <>
              <div className="flex items-center justify-between">
                <h4 className="font-semibold">{selected}</h4>
                <button className="btn btn-xs btn-ghost" onClick={()=>{ const next = { ...(personas||{}) }; delete next[selected]; onChange(next); setSelected(Object.keys(next)[0]||null); }}>Удалить</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="label text-sm opacity-70 mb-1">Activation cues</div>
                  <textarea
                    ref={semanticRef}
                    className="textarea textarea-bordered w-full min-h-24 max-h-72 whitespace-pre-wrap break-words leading-5 text-sm resize-y overflow-hidden"
                    placeholder="Themes/ideas, one per line"
                    value={(p.semantic_hints||[]).join('\n')}
                    wrap="soft"
                    onInput={(e)=>autoResize(e.currentTarget)}
                    onChange={(e)=>update([selected,'semantic_hints'], e.target.value.split('\n').map((s:string)=>s.trim()).filter(Boolean))}
                  />
                </div>
                <div>
                  <div className="label text-sm opacity-70 mb-1">Examples (≤160 chars each)</div>
                  <textarea
                    ref={examplesRef}
                    className="textarea textarea-bordered w-full min-h-32 max-h-72 whitespace-pre-wrap break-words leading-5 text-sm resize-y overflow-hidden"
                    placeholder="Short snippets, one per line"
                    value={(p.examples||[]).join('\n')}
                    wrap="soft"
                    onInput={(e)=>autoResize(e.currentTarget)}
                    onChange={(e)=>update([selected,'examples'], e.target.value.split('\n').map((s:string)=>s.trim()).filter(Boolean))}
                  />
                </div>
              </div>
              <div>
                <div className="label text-sm opacity-70 mb-1">Optional keywords</div>
                <textarea
                  ref={triggersRef}
                  className="textarea textarea-bordered w-full min-h-16 max-h-60 whitespace-pre-wrap break-words leading-5 text-sm resize-y overflow-hidden"
                  placeholder="1–2 words per line (optional)"
                  value={(p.triggers||[]).join('\n')}
                  wrap="soft"
                  onInput={(e)=>autoResize(e.currentTarget)}
                  onChange={(e)=>update([selected,'triggers'], e.target.value.split('\n').map((s:string)=>s.trim()).filter(Boolean))}
                />
              </div>
            </>
          ) : (
            <div className="opacity-70 text-sm">Добавьте суб‑персону слева.</div>
          )}
        </div>
      </div>

      {/* Tester */}
      <div className="md:col-span-4 card bg-base-200">
        <div className="card-body gap-2">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold">Test activation</h4>
          </div>
          <textarea
            ref={previewRef}
            className="textarea textarea-bordered w-full min-h-24 max-h-96 whitespace-pre-wrap break-words leading-5 text-sm resize-y overflow-hidden"
            placeholder="Вставьте пост для классификации"
            value={preview}
            wrap="soft"
            onInput={(e)=>autoResize(e.currentTarget)}
            onChange={(e)=>setPreview(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <button className="btn btn-sm" onClick={async()=>{
              const r = await onPreview(preview);
              if (r && r.full_scores){
                const ns:Record<string, number> = {};
                Object.entries(r.full_scores).forEach(([k,v]:any)=>{ ns[k] = v.score; });
                setScores(ns);
              }
            }}>Проверить</button>
          </div>
        </div>
      </div>
    </div>
  );
};


