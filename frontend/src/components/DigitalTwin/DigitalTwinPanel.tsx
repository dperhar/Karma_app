'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { userService } from '@/core/api/services/user-service';
import { User } from '@/types/user';
import { useWebSocket } from '@/hooks/useWebSocket';

interface DigitalTwinPanelProps {
  user: User;
  onUserUpdate?: (user: User) => void;
}

export const DigitalTwinPanel: React.FC<DigitalTwinPanelProps> = ({ 
  user, 
  onUserUpdate 
}) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [logs, setLogs] = useState<string[]>([]);
  const [aiProfile, setAiProfile] = useState<any | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [draftEdit, setDraftEdit] = useState<any>({});

  const initDataRaw = 'mock_init_data_for_telethon';
  const { lastMessage, isConnected } = useWebSocket({ userId: user.id, initDataRaw });

  // On mount, fetch AI profile once to hydrate status if backend already saved earlier
  useEffect(() => {
    (async () => {
      try {
        const aiProfile = await userService.getMyAIProfile(initDataRaw);
        if (aiProfile.success && aiProfile.data) {
          setAiProfile(aiProfile.data);
          if (onUserUpdate) {
            onUserUpdate({
              ...user,
              context_analysis_status: aiProfile.data.analysis_status ?? user.context_analysis_status,
              last_context_analysis_at: aiProfile.data.last_analyzed_at ?? user.last_context_analysis_at,
              persona_name: aiProfile.data.persona_name ?? user.persona_name,
            } as any);
          }
        }
      } catch {}
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const ts = new Date().toLocaleTimeString();
    setLogs((prev) => [
      `[${ts}] ${lastMessage.event}: ${JSON.stringify(lastMessage.data)}`,
      ...prev
    ].slice(0, 50));

    if (lastMessage.event === 'vibe_profile_analyzing') {
      setIsAnalyzing(true);
    }
    if (lastMessage.event === 'vibe_profile_completed') {
      setIsAnalyzing(false);
      // refresh user data to show new profile
      (async () => {
        try {
          const userResponse = await userService.getCurrentUser(initDataRaw);
          if (userResponse.success && userResponse.data && onUserUpdate) {
            onUserUpdate(userResponse.data);
          }
          // Also fetch AI profile to show persisted status even if user object lacks derived fields
          try {
            const aiProfile = await userService.getMyAIProfile(initDataRaw);
            if (aiProfile.success) {
              setLogs((prev) => [`[${new Date().toLocaleTimeString()}] ai_profile_refreshed: ${JSON.stringify(aiProfile.data)}`, ...prev].slice(0,50));
              // Optimistically update visible status/time from AI profile
              if (onUserUpdate && userResponse.success && userResponse.data) {
                onUserUpdate({
                  ...userResponse.data,
                  context_analysis_status: aiProfile.data?.analysis_status ?? user.context_analysis_status,
                  last_context_analysis_at: aiProfile.data?.last_analyzed_at ?? user.last_context_analysis_at,
                  persona_name: aiProfile.data?.persona_name ?? user.persona_name,
                } as any);
              }
              setAiProfile(aiProfile.data);
            }
          } catch {}
        } catch {}
      })();
    }
    if (lastMessage.event === 'vibe_profile_failed') {
      // If a dev-seed completion follows, suppress the error toast noise
      const likelyDevSeedNext = logs.find((l) => l.includes('dev_seed_done'));
      setIsAnalyzing(false);
      if (!likelyDevSeedNext) {
        setError(lastMessage.data?.error || 'Анализ не удался');
      }
    }
  }, [lastMessage, onUserUpdate]);

  const handleAnalyzeContext = async () => {
    if (isAnalyzing) return;
    
    setIsAnalyzing(true);
    setError('');
    setAnalysisResult('');

    try {
      console.log('Starting context analysis...');
      const response = await userService.analyzeUserContext("mock_init_data_for_telethon");
      
      if (response.success && response.data) {
        setAnalysisResult(`
Анализ завершен успешно!
Статус: ${response.data.status}
${response.data.style_description ? `Стиль общения: ${response.data.style_description}` : ''}
${response.data.system_prompt ? `System Prompt создан` : ''}
        `.trim());
        
        // Refresh user data if needed
        if (onUserUpdate) {
          try {
            const userResponse = await userService.getCurrentUser("mock_init_data_for_telethon");
            if (userResponse.success && userResponse.data) {
              onUserUpdate(userResponse.data);
            }
          } catch (e) {
            console.error('Failed to refresh user data:', e);
          }
        }
      } else {
        setError(response.message || 'Неизвестная ошибка');
      }
    } catch (err: any) {
      console.error('Context analysis failed:', err);
      setError(err.message || 'Ошибка при анализе контекста');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return 'Никогда';
    return new Date(dateString).toLocaleString('ru-RU');
  };

  const getStatusBadgeClass = (status: string | null | undefined) => {
    switch (status) {
      case 'COMPLETED': return 'badge-success';
      case 'PENDING': return 'badge-warning';
      case 'FAILED': return 'badge-error';
      default: return 'badge-neutral';
    }
  };

  const ProfileSummary: React.FC = () => {
    if (!aiProfile || aiProfile.analysis_status !== 'COMPLETED') return null;
    const vp = aiProfile.vibe_profile_json || {};
    const dm = vp.digital_comm || {};
    const markers = vp.style_markers || {};
    const arr = (v: any) => (Array.isArray(v) ? v : []);
    const phrases = arr(vp.signature_phrases).map((p: any) => typeof p === 'string' ? p : p?.text).filter(Boolean);

    return (
      <div className="card bg-base-200">
        <div className="card-body gap-4">
          <div className="flex flex-wrap items-center gap-2">
            {vp.tone && <span className="badge badge-outline">Тон: {vp.tone}</span>}
            {vp.verbosity && <span className="badge badge-outline">Детальность: {vp.verbosity}</span>}
            {vp.emoji_usage && <span className="badge badge-outline">Эмодзи: {vp.emoji_usage}</span>}
            {typeof markers.avg_sentence_len_words === 'number' && (
              <span className="badge badge-outline">Ср. длина фразы: {markers.avg_sentence_len_words}</span>
            )}
          </div>

          {arr(vp.topics_of_interest).length > 0 && (
            <div>
              <div className="label text-sm opacity-70 mb-1">Темы интересов</div>
              <div className="flex flex-wrap gap-2">
                {arr(vp.topics_of_interest).slice(0, 12).map((t: string) => (
                  <span key={t} className="badge badge-ghost">{t}</span>
                ))}
              </div>
            </div>
          )}

          {phrases.length > 0 && (
            <div>
              <div className="label text-sm opacity-70 mb-1">Фирменные фразы</div>
              <ul className="list-disc ml-6 text-sm">
                {phrases.slice(0, 8).map((p: string) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {(arr(dm.greetings).length || arr(dm.typical_endings).length) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {arr(dm.greetings).length > 0 && (
                <div>
                  <div className="label text-sm opacity-70 mb-1">Приветствия</div>
                  <div className="flex flex-wrap gap-2">
                    {arr(dm.greetings).map((g: string) => <span key={g} className="badge badge-ghost">{g}</span>)}
                  </div>
                </div>
              )}
              {arr(dm.typical_endings).length > 0 && (
                <div>
                  <div className="label text-sm opacity-70 mb-1">Типичные окончания</div>
                  <div className="flex flex-wrap gap-2">
                    {arr(dm.typical_endings).map((e: string) => <span key={e} className="badge badge-ghost">{e}</span>)}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {arr(vp.signature_templates).length > 0 && (
            <div>
              <div className="label text-sm opacity-70 mb-1">Шаблоны формулировок</div>
              <ul className="menu bg-base-100 rounded-box text-sm">
                {arr(vp.signature_templates).slice(0, 3).map((tpl: string, i: number) => (
                  <li key={`${i}-${tpl}`}><span>{tpl}</span></li>
                ))}
              </ul>
            </div>
          )}

          {(arr(vp.do_list).length || arr(vp.dont_list).length) ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {arr(vp.do_list).length > 0 && (
                <div>
                  <div className="label text-sm opacity-70 mb-1">Делать</div>
                  <ul className="list-disc ml-6 text-sm">
                    {arr(vp.do_list).slice(0, 6).map((d: string) => <li key={d}>{d}</li>)}
                  </ul>
                </div>
              )}
              {arr(vp.dont_list).length > 0 && (
                <div>
                  <div className="label text-sm opacity-70 mb-1">Не делать</div>
                  <ul className="list-disc ml-6 text-sm">
                    {arr(vp.dont_list).slice(0, 6).map((d: string) => <li key={d}>{d}</li>)}
                  </ul>
                </div>
              )}
            </div>
          ) : null}

          {vp.style_prompt && (
            <div>
              <div className="label text-sm opacity-70 mb-1">Как AI будет писать черновики</div>
              <div className="textarea textarea-bordered bg-base-100 text-sm whitespace-pre-wrap">
                {vp.style_prompt}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const onEditToggle = () => {
    if (!aiProfile) return;
    const vp = aiProfile.vibe_profile_json || {};
    setDraftEdit({
      persona_name: aiProfile.persona_name || '',
      user_system_prompt: aiProfile.user_system_prompt || '',
      tone: vp.tone || '',
      verbosity: vp.verbosity || '',
      emoji_usage: vp.emoji_usage || '',
      style_prompt: vp.style_prompt || '',
      topics_of_interest: Array.isArray(vp.topics_of_interest) ? vp.topics_of_interest : [],
      signature_templates: Array.isArray(vp.signature_templates) ? vp.signature_templates : [],
      do_list: Array.isArray(vp.do_list) ? vp.do_list : [],
      dont_list: Array.isArray(vp.dont_list) ? vp.dont_list : [],
      greetings: Array.isArray(vp.digital_comm?.greetings) ? vp.digital_comm.greetings : [],
      typical_endings: Array.isArray(vp.digital_comm?.typical_endings) ? vp.digital_comm.typical_endings : [],
      signature_phrases: (Array.isArray(vp.signature_phrases) ? vp.signature_phrases : []).map((p: any) => (typeof p === 'string' ? p : p?.text)).filter(Boolean),
    });
    setEditMode(true);
  };

  const saveEdits = async () => {
    try {
      const res = await userService.updateMyAIProfile(draftEdit, initDataRaw);
      if (res.success) {
        setAiProfile(res.data);
        setEditMode(false);
        // reflect in badge/time
        if (onUserUpdate) {
          onUserUpdate({
            ...user,
            context_analysis_status: res.data.analysis_status ?? user.context_analysis_status,
            last_context_analysis_at: res.data.last_analyzed_at ?? user.last_context_analysis_at,
            persona_name: res.data.persona_name ?? user.persona_name,
          } as any);
        }
      }
    } catch (e) {
      console.error('Failed to save AI profile edits', e);
    }
  };

  const TagInput = ({ label, value, onChange }: { label: string; value: string[]; onChange: (v: string[]) => void }) => {
    const [text, setText] = useState('');
    const add = () => {
      const v = text.trim();
      if (!v) return;
      onChange([...(value || []), v]);
      setText('');
    };
    const remove = (idx: number) => onChange(value.filter((_, i) => i !== idx));
    return (
      <div>
        <div className="label text-sm opacity-70 mb-1">{label}</div>
        <div className="flex flex-wrap gap-2 mb-2">
          {value?.map((v, i) => (
            <span key={`${v}-${i}`} className="badge badge-ghost gap-1">
              {v}
              <button className="btn btn-xs btn-ghost" onClick={() => remove(i)}>✕</button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input className="input input-bordered input-sm flex-1" value={text} onChange={(e) => setText(e.target.value)} placeholder="Add item" />
          <button className="btn btn-sm" onClick={add}>Добавить</button>
        </div>
      </div>
    );
  };

  return (
    <div className="card bg-base-100 shadow-xl">
      <div className="card-body">
        <h2 className="card-title text-primary">
          🤖 Цифровой Двойник
        </h2>
        
        <div className="space-y-4">
          {/* Status */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label text-sm opacity-70">Статус анализа:</label>
              <span className={`badge ${getStatusBadgeClass(user.context_analysis_status)}`}>
                {user.context_analysis_status || 'НЕ АНАЛИЗИРОВАЛСЯ'}
              </span>
            </div>
            <div>
              <label className="label text-sm opacity-70">Последний анализ:</label>
              <span className="text-sm">
                {formatDate(user.last_context_analysis_at)}
              </span>
            </div>
          </div>

          {/* Live Progress */}
          <div className="grid grid-cols-1 gap-2">
            <div className="flex items-center gap-2">
              <span className={`badge ${isAnalyzing ? 'badge-warning' : 'badge-ghost'}`}>
                {isAnalyzing ? 'Идет анализ (реальное время)...' : isConnected ? 'WS connected' : 'WS disconnected'}
              </span>
              {isAnalyzing && <span className="loading loading-dots loading-sm" />}
            </div>
            {isAnalyzing && (
              <progress className="progress progress-primary w-full" />
            )}
          </div>

          {/* Debug Logs */}
          <details className="collapse collapse-arrow bg-base-200">
            <summary className="collapse-title text-sm">Debug Logs</summary>
            <div className="collapse-content">
              <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">
                {logs.join('\n') || 'No events yet'}
              </pre>
            </div>
          </details>

          {/* AI Profile Summary */}
          <div className="flex justify-between items-center">
            <h3 className="font-semibold">Профиль ИИ</h3>
            {aiProfile?.analysis_status === 'COMPLETED' && (
              <button className="btn btn-sm" onClick={onEditToggle}>
                {editMode ? 'Отмена' : 'Редактировать'}
              </button>
            )}
          </div>
          {!editMode ? (
            <ProfileSummary />
          ) : (
            <div className="card bg-base-200">
              <div className="card-body grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="label text-sm opacity-70 mb-1">Имя персоны</div>
                  <input className="input input-bordered w-full" value={draftEdit.persona_name || ''} onChange={(e)=>setDraftEdit({...draftEdit, persona_name: e.target.value})} />
                </div>
                <div>
                  <div className="label text-sm opacity-70 mb-1">Тон</div>
                  <input className="input input-bordered w-full" value={draftEdit.tone || ''} onChange={(e)=>setDraftEdit({...draftEdit, tone: e.target.value})} />
                </div>
                <div>
                  <div className="label text-sm opacity-70 mb-1">Детальность</div>
                  <input className="input input-bordered w-full" value={draftEdit.verbosity || ''} onChange={(e)=>setDraftEdit({...draftEdit, verbosity: e.target.value})} />
                </div>
                <div>
                  <div className="label text-sm opacity-70 mb-1">Эмодзи</div>
                  <input className="input input-bordered w-full" value={draftEdit.emoji_usage || ''} onChange={(e)=>setDraftEdit({...draftEdit, emoji_usage: e.target.value})} />
                </div>
                <div className="md:col-span-2">
                  <div className="label text-sm opacity-70 mb-1">Как AI будет писать черновики</div>
                  <textarea className="textarea textarea-bordered w-full min-h-24" value={draftEdit.style_prompt || ''} onChange={(e)=>setDraftEdit({...draftEdit, style_prompt: e.target.value})} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Темы интересов" value={draftEdit.topics_of_interest || []} onChange={(v)=>setDraftEdit({...draftEdit, topics_of_interest: v})} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Шаблоны формулировок" value={draftEdit.signature_templates || []} onChange={(v)=>setDraftEdit({...draftEdit, signature_templates: v})} />
                </div>
                <div>
                  <TagInput label="Делать" value={draftEdit.do_list || []} onChange={(v)=>setDraftEdit({...draftEdit, do_list: v})} />
                </div>
                <div>
                  <TagInput label="Не делать" value={draftEdit.dont_list || []} onChange={(v)=>setDraftEdit({...draftEdit, dont_list: v})} />
                </div>
                <div>
                  <TagInput label="Приветствия" value={draftEdit.greetings || []} onChange={(v)=>setDraftEdit({...draftEdit, greetings: v})} />
                </div>
                <div>
                  <TagInput label="Типичные окончания" value={draftEdit.typical_endings || []} onChange={(v)=>setDraftEdit({...draftEdit, typical_endings: v})} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Фирменные фразы" value={draftEdit.signature_phrases || []} onChange={(v)=>setDraftEdit({...draftEdit, signature_phrases: v})} />
                </div>
                <div className="md:col-span-2 flex justify-end gap-2">
                  <button className="btn" onClick={()=>setEditMode(false)}>Отмена</button>
                  <button className="btn btn-primary" onClick={saveEdits}>Сохранить</button>
                </div>
              </div>
            </div>
          )}

          {/* Style Description */}
          {user.persona_style_description && (
            <div>
              <label className="label text-sm opacity-70">Стиль общения:</label>
              <div className="textarea textarea-bordered bg-base-200 text-sm">
                {user.persona_style_description}
              </div>
            </div>
          )}

          {/* Interests */}
          {user.persona_interests_json && (
            <div>
              <label className="label text-sm opacity-70">Интересы:</label>
              <div className="textarea textarea-bordered bg-base-200 text-sm">
                {JSON.stringify(JSON.parse(user.persona_interests_json), null, 2)}
              </div>
            </div>
          )}

          {/* System Prompt Status */}
          {user.user_system_prompt && (
            <div className="alert alert-success">
              <span>✅ AI System Prompt создан и готов к использованию</span>
            </div>
          )}

          {/* Analysis Button */}
          <div className="card-actions justify-center">
            <button 
              className={`btn btn-primary ${isAnalyzing ? 'loading' : ''}`}
              onClick={handleAnalyzeContext}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? 'Анализирую...' : '🔍 Анализировать Контекст'}
            </button>
          </div>

          {/* Results */}
          {analysisResult && (
            <div className="alert alert-success">
              <pre className="text-sm whitespace-pre-wrap">{analysisResult}</pre>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="alert alert-error">
              <span>❌ {error}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}; 