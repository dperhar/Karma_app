'use client';

import React, { useMemo, useState, useEffect } from 'react';
import { userService } from '@/core/api/services/user-service';
import { SubPersonaPanel } from '@/components/DigitalTwin/SubPersonaPanel';
import { User } from '@/types/user';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useRouter } from 'next/navigation';
import { postService } from '@/core/api/services/post-service';
import { useCommentStore, DraftComment } from '@/store/commentStore';
import DraftCard from '@/components/DraftCard';

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
  const [draftLogs, setDraftLogs] = useState<string[]>([]);
  const [aiProfile, setAiProfile] = useState<any | null>(null);
  const [editMode, setEditMode] = useState(true);
  const [draftEdit, setDraftEdit] = useState<any>({});
  const [isSaving, setIsSaving] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null);
  // Realtime analysis UX state
  const [stage, setStage] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [stageInfo, setStageInfo] = useState<any>({});
  const hydratedRef = React.useRef(false);
  const [newSubPersona, setNewSubPersona] = useState('');
  const [previewText, setPreviewText] = useState('');
  const [previewResult, setPreviewResult] = useState<{persona:string|null; score:number; semantic:number; keywords:number} | null>(null);
  // Freeform compiler UI state
  const [freeform, setFreeform] = useState('');
  const [ffStatus, setFfStatus] = useState<'idle'|'queued'|'applying'|'error'|'done'>('idle');
  const [ffPreview, setFfPreview] = useState<any | null>(null);
  const [ffNotes, setFfNotes] = useState<string[]>([]);
  const [ffTokens, setFfTokens] = useState<number | null>(null);
  const [applyMask, setApplyMask] = useState<Record<string, boolean>>({ persona: true, dynamic_filters: true, state_model: true, core_tensions: true, style_dna: true, generation_controls: false, anti_generic: false });
  const [strategy, setStrategy] = useState<'merge'|'replace'>('merge');
  // Draft control center state
  const { drafts, fetchDrafts, updateDraft, postDraft, regenerateDraft, upsertDraft } = useCommentStore();
  const latestFiveDrafts = useMemo(() => {
    try {
      return [...drafts]
        .sort((a,b)=> new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime())
        .slice(0,5);
    } catch { return drafts.slice(0,5); }
  }, [drafts]);
  const [editingDrafts, setEditingDrafts] = useState<Record<string, string>>({});
  const [regenFeedback, setRegenFeedback] = useState<Record<string, string>>({});
  const [openBubbleKey, setOpenBubbleKey] = useState<string | null>(null);
  const [genSource, setGenSource] = useState<'channels'|'both'|'groups'>('channels');
  const [genPage, setGenPage] = useState<number>(1);
  const currentDtConfig = useMemo(() => {
    const vp: any = aiProfile?.vibe_profile_json || {};
    return vp?.dt_config || null;
  }, [aiProfile]);
  // Helper text for each mask toggle so users know the impact
  const maskHelp: Record<string, string> = useMemo(() => ({
    persona: 'Voice, tone, and lexicon. Uncheck to keep your current voice unchanged (avoid “softening”).',
    dynamic_filters: 'Sub-personalities, trauma hints, environment. Check to add new parts discovered in freeform.',
    state_model: 'IFS state model: core self and parts with rules. Uncheck to avoid deep structural changes.',
    core_tensions: 'Adds or updates tension axes (e.g., integration_vs_conflict). Keep checked to retain “third way”.',
    style_dna: 'Prosody/rhetoric metrics derived from text. Uncheck to keep your current style limits.',
    generation_controls: 'Length, candidates, question ratio, anchors, etc. Check if freeform sets writing controls.',
    anti_generic: 'Stop phrases and anti-generic guards. Check to update banned openers from your freeform.',
  }), []);

  // Safe deep path initializer
  const ensurePath = (root: any, path: (string|number)[], defaultLeaf: any) => {
    let cur = root;
    for (let i = 0; i < path.length - 1; i++) {
      const key = path[i] as any;
      if (cur[key] === undefined || typeof cur[key] !== 'object') {
        cur[key] = {};
      }
      cur = cur[key];
    }
    const lastKey = path[path.length - 1] as any;
    if (cur[lastKey] === undefined) {
      cur[lastKey] = defaultLeaf;
    }
    return root;
  };

  const initDataRaw = 'mock_init_data_for_telethon';
  const { lastMessage, isConnected } = useWebSocket({ userId: user.id, initDataRaw });
  const [activeTab, setActiveTab] = useState<'persona'|'alignment'|'generation'|'learning'>('persona');
  const router = useRouter();

  const buildFreeformFromVibe = (vp: any): string => {
    try {
      const tone = vp?.tone || vp?.dt_config?.persona?.voice?.tone || '';
      const lex = vp?.dt_config?.persona?.voice?.lexicon || {};
      const sys = Array.isArray(lex?.system) ? lex.system.slice(0, 12) : [];
      const psy = Array.isArray(lex?.psychology) ? lex.psychology.slice(0, 12) : [];
      const dir = Array.isArray(lex?.direct) ? lex.direct.slice(0, 12) : [];
      const stop = (vp?.dt_config?.anti_generic?.stop_phrases || []).slice(0, 12);
      const subp = vp?.dt_config?.dynamic_filters?.sub_personalities || {};
      const subpList = Object.keys(subp || {}).slice(0, 8);
      const sig = (vp?.signature_phrases || []).map((p: any) => (typeof p === 'string' ? p : p?.text)).filter(Boolean).slice(0, 10);
      const tensions = (vp?.core_tensions?.axes || []).map((a: any) => a?.name).filter(Boolean).slice(0, 6);
      const rq = vp?.dt_config?.generation_controls?.rhetoric?.question_ratio_target;
      return [
        'Persona Voice:',
        `- tone: ${tone}`,
        `- lexicon.system: ${sys.join(', ')}`,
        `- lexicon.psychology: ${psy.join(', ')}`,
        `- lexicon.direct: ${dir.join(', ')}`,
        `- banned_openers: ${stop.join(', ')}`,
        '',
        'Sub-personalities:',
        `- ${subpList.join(', ') || '—'}`,
        '',
        'Core tensions:',
        `- ${tensions.join(', ') || '—'}`,
        '',
        'Style controls:',
        rq !== undefined ? `- question_ratio_target: ${rq}` : '',
        '',
        'Signature phrases:',
        `- ${sig.join(', ') || '—'}`,
      ].filter(Boolean).join('\n');
    } catch (e) {
      return '';
    }
  };

  // On mount, fetch AI profile once to hydrate status if backend already saved earlier
  useEffect(() => {
    (async () => {
      try {
        const aiProfile = await userService.getMyAIProfile(initDataRaw);
        if (aiProfile.success && aiProfile.data) {
          setAiProfile(aiProfile.data);
          // hydrate editor by default so user can edit immediately
          try {
            const vp = aiProfile.data.vibe_profile_json || {};
            setDraftEdit({
              persona_name: aiProfile.data.persona_name || '',
              user_system_prompt: aiProfile.data.user_system_prompt || '',
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
              dt_config: {
                persona: vp.dt_config?.persona || {},
                dynamic_filters: {
                  sub_personalities: vp.dt_config?.dynamic_filters?.sub_personalities || {},
                  trauma_response: vp.dt_config?.dynamic_filters?.trauma_response || {},
                  environment: vp.dt_config?.dynamic_filters?.environment || {},
                },
                decoding: vp.dt_config?.decoding || {},
                generation_controls: vp.dt_config?.generation_controls || {},
                anti_generic: vp.dt_config?.anti_generic || {},
                style_metrics: vp.dt_config?.style_metrics || {},
              },
            });
            hydratedRef.current = true;
          } catch {}
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
    const line = (label:string, data:any) => `[${ts}] ${label}: ${JSON.stringify(data)}`;
    if (lastMessage.event === 'new_ai_draft') {
      setDraftLogs((prev)=>[line('new_ai_draft', lastMessage.data), ...prev].slice(0,150));
      try { if ((lastMessage.data as any)?.draft) upsertDraft((lastMessage.data as any).draft as DraftComment); } catch {}
    } else if (lastMessage.event === 'draft_generation_queued') {
      setDraftLogs((prev)=>[line('draft_generation_queued', lastMessage.data), ...prev].slice(0,150));
    } else if (lastMessage.event === 'draft_generation_failed') {
      setDraftLogs((prev)=>[line('draft_generation_failed', lastMessage.data), ...prev].slice(0,150));
    } else {
      setLogs((prev) => [line(lastMessage.event, lastMessage.data), ...prev].slice(0, 100));
    }

    if (lastMessage.event === 'dt_freeform_decision') {
      setLogs((prev)=>[line('dt_freeform_decision', lastMessage.data), ...prev].slice(0,100));
    }

    // Map worker stages to human labels and progress
    const STAGES: Record<string, { label: string; pct: number }> = {
      start: { label: 'Запуск анализа', pct: 5 },
      tg_connecting: { label: 'Подключение к Telegram', pct: 10 },
      tg_connected: { label: 'Telegram подключен', pct: 15 },
      fetch_start: { label: 'Собираем сообщения', pct: 25 },
      fetch_done: { label: 'Сообщения собраны', pct: 35 },
      fetch_sample: { label: 'Готовим статистику', pct: 45 },
      llm_prepare: { label: 'Формируем подсказку для ИИ', pct: 55 },
      llm_start: { label: 'ИИ анализирует стиль', pct: 70 },
      llm_response_received: { label: 'Обрабатываем результат', pct: 80 },
      persist_done: { label: 'Сохраняем профиль', pct: 90 },
      done: { label: 'Готово', pct: 100 },
      insufficient_data: { label: 'Недостаточно данных', pct: 100 },
      llm_failed: { label: 'Сбой ИИ', pct: 100 },
    };

    if (lastMessage.event === 'vibe_profile_status') {
      const s = String((lastMessage.data || {}).stage || 'start');
      setStage(s);
      setStageInfo(lastMessage.data || {});
      const target = STAGES[s];
      if (target) setProgress((p) => Math.max(p, target.pct));
      setIsAnalyzing(s !== 'done');
    }

    if (lastMessage.event === 'vibe_profile_analyzing') {
      setIsAnalyzing(true);
      setStage('start');
      setProgress(5);
    }
    if (lastMessage.event === 'vibe_profile_completed') {
      setIsAnalyzing(false);
      setStage('done');
      setProgress(100);
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
      setStage('llm_failed');
      if (!likelyDevSeedNext) {
        setError(lastMessage.data?.error || 'Анализ не удался');
      }
    }
    if (lastMessage.event === 'dt_freeform_status') {
      setFfStatus('queued');
    }
    if (lastMessage.event === 'dt_freeform_preview') {
      setFfStatus('done');
      setFfPreview((lastMessage.data as any)?.parsed_dt_config || null);
      const notes = (((lastMessage.data as any)?.compiler_notes?.warnings)||[]) as string[];
      setFfNotes(notes);
      setFfTokens(Number(((lastMessage.data as any)?.tokens_estimate)||0));
    }
    if (lastMessage.event === 'dt_freeform_completed') {
      setFfStatus('done');
    }
    if (lastMessage.event === 'dt_freeform_failed') {
      setFfStatus('error');
      setError((lastMessage.data as any)?.error || 'Freeform compiler failed');
    }
    if (lastMessage.event === 'dt_freeform_seeded') {
      try {
        const seed = (lastMessage.data as any)?.freeform || '';
        if (seed && (!freeform || freeform.trim().length < 10)) {
          setFreeform(seed);
          setFfStatus('queued'); setFfPreview(null); setFfNotes([]); setError('');
          userService.dtFreeformPreview(seed, initDataRaw).catch(()=>{});
        }
      } catch {}
    }
  }, [lastMessage, onUserUpdate]);

  // Draft edit helpers for Alignment tab
  const handleEditChange = (draftId: string, text: string) => {
    const [baseId, field] = draftId.split('::');
    if (field) {
      setRegenFeedback(prev => ({ ...prev, [`ctx:${baseId}:${field}`]: text }));
    } else {
      setEditingDrafts(prev => ({ ...prev, [draftId]: text }));
    }
  };

  const handleSaveEdit = async (draftId: string) => {
    const text = editingDrafts[draftId];
    const gp: Record<string, any> = {};
    for (const [k, v] of Object.entries(regenFeedback)) {
      if (k.startsWith(`ctx:${draftId}:`)) {
        const field = k.split(':')[2];
        gp[field] = field === 'is_style_example' ? String(v).toLowerCase() === 'true' : v;
      }
    }
    await updateDraft(draftId, text ?? '', initDataRaw, Object.keys(gp).length ? gp : undefined);
  };

  const handleSend = async (draftId: string) => {
    await handleSaveEdit(draftId);
    await postDraft(draftId, initDataRaw);
  };

  const handleRegenerate = async (draft: DraftComment) => {
    const feedback = regenFeedback[draft.id];
    await regenerateDraft(
      draft.id,
      { original_message_id: String(draft.original_message_id), text: draft.original_post_content as any },
      feedback,
      initDataRaw
    );
    setRegenFeedback((prev) => ({ ...prev, [draft.id]: '' }));
    setEditingDrafts((prev) => { const c = { ...prev }; delete c[draft.id]; return c; });
  };

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
      dt_config: {
        persona: vp.dt_config?.persona || {},
        dynamic_filters: {
          sub_personalities: vp.dt_config?.dynamic_filters?.sub_personalities || {},
          trauma_response: vp.dt_config?.dynamic_filters?.trauma_response || {},
          environment: vp.dt_config?.dynamic_filters?.environment || {},
        },
        decoding: vp.dt_config?.decoding || {},
        generation_controls: vp.dt_config?.generation_controls || {},
        anti_generic: vp.dt_config?.anti_generic || {},
        style_metrics: vp.dt_config?.style_metrics || {},
      },
    });
    setEditMode(true);
  };

  const saveEdits = async () => {
    try {
      setIsSaving(true);
      const payload: any = { ...draftEdit };
      if (payload.dt_config && payload.dt_config.dynamic_filters) {
        const df = payload.dt_config.dynamic_filters as any;
        delete (df as any).hd_profile;
      }
      if (payload.dt_config) {
        delete (payload.dt_config as any).astro_axis;
      }
      const res = await userService.updateMyAIProfile(payload, initDataRaw);
      if (res.success) {
        setAiProfile(res.data);
        setLastSavedAt(Date.now());
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
    } finally { setIsSaving(false); }
  };

  const TagInput = ({ label, value, onChange, placeholder }: { label: string; value: string[]; onChange: (v: string[]) => void; placeholder?: string }) => {
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
          <input className="input input-bordered input-sm flex-1" value={text} onChange={(e) => setText(e.target.value)} placeholder={placeholder || "Add item"} />
          <button className="btn btn-sm" onClick={add}>Добавить</button>
        </div>
      </div>
    );
  };

  const InfoTip: React.FC<{ text: string; side?: 'left'|'right'|'top'|'bottom' }> = ({ text, side = 'right' }) => (
    <span className={`tooltip tooltip-${side}`} data-tip={text} aria-label={text}>
      <span className="badge badge-ghost badge-xs cursor-help select-none">i</span>
    </span>
  );

  // Global debounced autosave when any draftEdit field changes (after initial hydrate)
  useEffect(() => {
    if (!hydratedRef.current) return;
    const h = setTimeout(() => { saveEdits(); }, 1000);
    return () => clearTimeout(h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftEdit]);

  return (
    <div className="card bg-base-100 shadow-xl">
      <div className="card-body">
        <h2 className="card-title text-primary">🤖 Цифровой Двойник</h2>
        <div className="tabs tabs-boxed w-full max-w-full overflow-x-auto">
          <a className={`tab ${activeTab==='persona'?'tab-active':''}`} onClick={()=>setActiveTab('persona')}>Persona</a>
          <a className={`tab ${activeTab==='alignment'?'tab-active':''}`} onClick={()=>setActiveTab('alignment')}>Alignment</a>
          {/* Generation merged into Alignment – tab intentionally removed */}
          <a className={`tab ${activeTab==='learning'?'tab-active':''}`} onClick={()=>setActiveTab('learning')}>Learning</a>
        </div>
        <div className="flex items-center justify-between mt-2">
          <div className="text-xs opacity-70">
            Последний анализ: {formatDate((aiProfile as any)?.last_analyzed_at || user.last_context_analysis_at)}
          </div>
          <button
            className="btn btn-sm btn-primary"
            onClick={async ()=>{
              try {
                await postService.queueGenerateForPage(undefined as any, 1, 20, 'channels');
              } catch {}
              router.push('/');
            }}
          >
            Start drafting
          </button>
        </div>
        
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
                {formatDate((aiProfile as any)?.last_analyzed_at || user.last_context_analysis_at)}
              </span>
            </div>
          </div>

          {/* Live Progress */}
          <div className="grid grid-cols-1 gap-2">
            <div className="flex items-center gap-2">
              <span className={`badge ${isAnalyzing ? 'badge-warning' : 'badge-ghost'}`}>
                {isAnalyzing ? (stage ? `Идёт анализ: ${stage}` : 'Идет анализ (реальное время)...') : isConnected ? 'WS connected' : 'WS disconnected'}
              </span>
              {isAnalyzing && (
                <span className="text-xs opacity-70">
                  {(() => {
                    const labels: Record<string,string> = {
                      start:'Запуск', tg_connecting:'Подключение к Telegram', tg_connected:'Telegram подключен', fetch_start:'Сбор сообщений', fetch_done:'Сообщения собраны', fetch_sample:'Готовим статистику', llm_prepare:'Готовим подсказку', llm_start:'ИИ анализирует', llm_response_received:'Обработка результата', persist_done:'Сохранение', done:'Готово', llm_failed:'Сбой ИИ', insufficient_data:'Недостаточно данных'
                    };
                    return labels[stage || 'start'] || 'Идет анализ';
                  })()}
                </span>
              )}
            </div>
            {isAnalyzing && (
              <progress className="progress progress-primary w-full" value={progress} max={100} />
            )}
          </div>

          {activeTab==='persona' && (
          <details className="collapse collapse-arrow bg-base-200">
              <summary className="collapse-title text-sm">Digital Twin Analysis Logs</summary>
            <div className="collapse-content">
                <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">
                  {logs.join('\n') || 'No events yet'}
                </pre>
            </div>
          </details>
          )}

          {/* AI Drafts Generation Logs (visible) */}
          <details className="collapse collapse-arrow bg-base-200">
              <summary className="collapse-title text-sm">AI Drafts Generation Logs</summary>
            <div className="collapse-content">
                <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">{draftLogs.join('\n') || 'No drafts yet'}</pre>
            </div>
          </details>

          {/* Alignment & Drift (read-only) */}
          {activeTab==='alignment' && aiProfile?.vibe_profile_json && (
            <div className="card bg-base-200">
              <div className="card-body gap-3">
                <h3 className="font-semibold">Alignment & Drift</h3>
                {(() => {
                  const vp: any = aiProfile?.vibe_profile_json || {};
                  const al: any = vp.alignment || {};
                  const dr: any = vp.drift || {};
                  const lhr = al.lexicon_hit_rate || {};
                  const pct = (v: number) => `${Math.max(0, Math.min(1, Number(v)||0))*100|0}%`;
                  return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="label text-sm opacity-70 mb-1">Lexicon hit rate</div>
                        <div className="space-y-2 text-xs">
                          {['system','psychology','direct'].map(k => (
                            <div key={k}>
                              <div className="flex justify-between"><span>{k}</span><span>{pct(lhr[k]||0)}</span></div>
                              <progress className="progress progress-primary w-full" value={(Math.max(0, Math.min(1, Number(lhr[k]||0)))*100)} max={100} />
            </div>
                          ))}
          </div>
                        <div className="mt-3 text-xs">
                          <div className="flex justify-between"><span>Tone alignment</span><span>{pct(al.tone_alignment||0)}</span></div>
                          <progress className="progress w-full" value={(Math.max(0, Math.min(1, Number(al.tone_alignment||0)))*100)} max={100} />
                        </div>
                        <div className="mt-3 text-xs">
                          <div className="flex justify-between"><span>Rhetoric alignment (question)</span><span>{pct(al?.rhetoric_alignment?.question||0)}</span></div>
                          <progress className="progress w-full" value={(Math.max(0, Math.min(1, Number(al?.rhetoric_alignment?.question||0)))*100)} max={100} />
                        </div>
                      </div>
                      <div>
                        <div className="label text-sm opacity-70 mb-1">Drift</div>
                        <div className="text-xs grid grid-cols-2 gap-2">
                          <span className="badge badge-ghost">tone_drift: {dr.tone_drift ?? 0}</span>
                          <span className="badge badge-ghost">rhetoric_drift: {dr.rhetoric_drift ?? 0}</span>
                          <span className="badge badge-ghost">language_mix_drift: {dr.language_mix_drift ?? 0}</span>
                          <span className="badge badge-ghost">violations: {al?.stop_phrase_violations?.count ?? 0}</span>
                        </div>
                        {Array.isArray(dr.lexicon_outliers) && dr.lexicon_outliers.length > 0 && (
                          <div className="mt-3">
                            <div className="label text-sm opacity-70 mb-1">Lexicon outliers</div>
                            <div className="flex flex-wrap gap-2 text-xs">
                              {dr.lexicon_outliers.slice(0, 20).map((w: string) => (
                                <span key={w} className="badge badge-outline">{w}</span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })()}
                <div className="divider" />
                {/* Quick fixes */}
                {(() => {
                  const vp: any = aiProfile?.vibe_profile_json || {};
                  const al: any = vp.alignment || {};
                  const dr: any = vp.drift || {};
                  return (
                    <div className="flex flex-wrap gap-2 text-xs">
                      <button className="btn btn-xs" onClick={()=>{
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev||{}));
                          // set question_ratio_target to 0.6
                          ensurePath(next,["dt_config","generation_controls","rhetoric"],{});
                          next.dt_config.generation_controls.rhetoric.question_ratio_target = 0.6;
                          return next;
                        })
                      }}>Set question_ratio_target → 0.6</button>
                      <button className="btn btn-xs" onClick={()=>{
                        const out: string[] = (dr.lexicon_outliers||[]).slice(0,5);
                        if (!out.length) return;
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev||{}));
                          ensurePath(next,["dt_config","persona","voice","lexicon"],{});
                          const arr = Array.isArray(next.dt_config.persona.voice.lexicon.system)?next.dt_config.persona.voice.lexicon.system:[];
                          out.forEach((w)=>{ if (arr.indexOf(w)===-1) arr.push(w); });
                          next.dt_config.persona.voice.lexicon.system = arr;
                          return next;
                        })
                      }}>Promote 5 outliers → lexicon.system</button>
                      <button className="btn btn-xs" onClick={()=>{
                        const ex: string[] = ((al.stop_phrase_violations?.examples)||[]).slice(0,5);
                        if (!ex.length) return;
                        const starters = ex.map(s=> String(s||'').split(/\s+/).slice(0,2).join(' ').trim()).filter(Boolean);
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev||{}));
                          ensurePath(next,["dt_config","anti_generic"],{});
                          const arr = Array.isArray(next.dt_config.anti_generic.stop_phrases)?next.dt_config.anti_generic.stop_phrases:[];
                          starters.forEach((w)=>{ if (arr.indexOf(w)===-1) arr.push(w); });
                          next.dt_config.anti_generic.stop_phrases = arr;
                          return next;
                        })
                      }}>Add violations → stop_phrases</button>
                    </div>
                  )
                })()}
                <div className="divider" />
                {/* Draft Control Center: generate and manage drafts in-place */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs opacity-70">Generate for:</span>
                    {(['channels','both','groups'] as const).map((s)=> (
                      <button key={s} className={`btn btn-xs ${genSource===s?'btn-primary':'btn-ghost'}`} onClick={()=>setGenSource(s)}>
                        {s}
                      </button>
                    ))}
                    <span className="text-xs opacity-70 ml-2">Page</span>
                    <input type="number" min={1} value={genPage} onChange={(e)=>setGenPage(Math.max(1, parseInt(e.target.value||'1',10)))} className="input input-xs input-bordered w-16" />
                  </div>
                  <div className="flex items-center gap-2">
                    <button className="btn btn-sm" onClick={async()=>{ try { await postService.queueGenerateForPage(undefined as any, genPage, 20, genSource); await fetchDrafts(undefined as any); setDraftLogs((p)=>[`[${new Date().toLocaleTimeString()}] queued_generate_page source=${genSource} page=${genPage}`, ...p].slice(0,150)); } catch(e){ setDraftLogs((p)=>[`[${new Date().toLocaleTimeString()}] queue_failed ${(e as any)?.message||e}`, ...p].slice(0,150)); } }}>Generate 20 drafts</button>
                    <button className="btn btn-sm btn-ghost" onClick={async()=>{ await fetchDrafts(undefined as any); }}>Refresh</button>
                  </div>
                </div>
                <div className="mt-3 space-y-4">
                  {latestFiveDrafts.map((d)=> (
                    <DraftCard key={d.id} draft={d as any} editingText={editingDrafts[d.id]} feedback={regenFeedback[d.id]} openBubbleKey={openBubbleKey} onChangeText={(t)=>handleEditChange(d.id, t)} onSend={()=>handleSend(d.id)} onRegenerate={()=>handleRegenerate(d)} onToggleChannelCtx={()=>setOpenBubbleKey((prev)=> prev===`chan:${d.id}`?null:`chan:${d.id}`)} onToggleMsgCtx={()=>setOpenBubbleKey((prev)=> prev===`msg:${d.id}`?null:`msg:${d.id}`)} onCtxChange={(fieldKey,value)=>handleEditChange(fieldKey, value)} onCtxSave={()=>handleSaveEdit(d.id)} onCtxClose={()=>setOpenBubbleKey(null)} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Digital Twin Freeform Compiler */}
          {(activeTab==='persona') && (
          <div className="card bg-base-200">
            <div className="card-body gap-3">
              {activeTab==='persona' && (<div className="flex items-center justify-between gap-2">
                <h3 className="font-semibold">Freeform Compiler</h3>
                <div className="flex items-center gap-2">
                  <button className="btn btn-xs" onClick={async()=>{
                    try {
                      // Kick off ultra-light reseed from cached messages (WS will deliver)
                      userService.dtFreeformSeedFromCache(initDataRaw).catch(()=>{});
                      // Also provide deterministic seed from current profile immediately
                      const seeded = await userService.dtFreeformSeedFromProfile(initDataRaw);
                      if (seeded.success && (seeded.data as any)?.freeform) {
                        const seed = (seeded.data as any).freeform;
                        setFreeform(seed);
                        setFfStatus('queued'); setFfPreview(null); setFfNotes([]); setError('');
                        try { await userService.dtFreeformPreview(seed, initDataRaw); } catch {}
                      }
                      // In parallel, kick off deeper analysis to refresh base data
                      userService.analyzeUserContext(initDataRaw as any).catch(()=>{});
                    } catch {}
                  }}>Analyze chats context → Seed</button>
                  <InfoTip text="Builds a starter freeform from your latest analyzed Telegram comments and group chats. To refresh the source, go to Analyze and run a new analysis." />
                  <span className={`badge ${ffStatus==='queued'?'badge-warning':ffStatus==='error'?'badge-error':ffStatus==='done'?'badge-success':'badge-ghost'}`}>{ffStatus}</span>
                </div>
              </div>)}
              {activeTab==='persona' && isAnalyzing && (
                <div className="flex items-center gap-2 text-xs">
                  <progress className="progress progress-primary w-40" value={progress} max={100} />
                  <span>{Math.round(progress)}%</span>
                  <span className="opacity-70">
                    {(() => {
                      const labels: Record<string,string> = {
                        start:'Запуск', tg_connecting:'Подключение к Telegram', tg_connected:'Telegram подключен', fetch_start:'Сбор сообщений', fetch_done:'Сообщения собраны', fetch_sample:'Готовим статистику', llm_prepare:'Готовим подсказку', llm_start:'ИИ анализирует', llm_response_received:'Обработка результата', persist_done:'Сохранение', done:'Готово', llm_failed:'Сбой ИИ', insufficient_data:'Недостаточно данных'
                      };
                      return labels[stage || 'start'] || 'Идет анализ';
                    })()}
                  </span>
                </div>
              )}
              {activeTab==='persona' && (
                <>
                  <textarea className="textarea textarea-bordered w-full min-h-40" placeholder="Вставьте фрифлоу (описание тона, ценностей, подличностей, запреты)…" value={freeform} onChange={(e)=>setFreeform(e.target.value)} />
                  <div className="text-xs opacity-60 flex items-center justify-between">
                    <span>Символов: {freeform.length}</span>
                    <span className="flex items-center gap-2">{isConnected ? 'WS connected' : 'WS disconnected'}</span>
                  </div>
                  <div className="text-xs opacity-60">
                    Источник: прошлые комментарии и чаты, проанализированные {formatDate((aiProfile as any)?.last_analyzed_at || user.last_context_analysis_at)}.
                  </div>
                </>
              )}
              {activeTab==='persona' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="card bg-base-100">
                  <div className="card-body gap-2">
                    <h4 className="font-semibold text-sm">Маска применения</h4>
                    {Object.entries(maskHelp).map(([k, tip]) => (
                      <label key={k} className="label cursor-pointer justify-between gap-2 text-xs">
                        <span className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            className="toggle toggle-xs"
                            checked={Boolean(applyMask[k])}
                            onChange={(e)=>setApplyMask({...applyMask, [k]: e.target.checked})}
                          />
                          <span>{k}</span>
                        </span>
                        <InfoTip text={tip} />
                      </label>
                    ))}
                    <div className="divider my-2" />
                    <div className="flex items-center gap-3 text-xs">
                      <label className="flex items-center gap-1"><input type="radio" name="ff-strategy" className="radio radio-xs" checked={strategy==='merge'} onChange={()=>setStrategy('merge')} /> merge</label>
                      <label className="flex items-center gap-1"><input type="radio" name="ff-strategy" className="radio radio-xs" checked={strategy==='replace'} onChange={()=>setStrategy('replace')} /> replace</label>
                    </div>
                  </div>
                </div>
                <div className="card bg-base-100 md:col-span-2">
                  <div className="card-body gap-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-sm">Preview (active if not overridden)</h4>
                      <div className="flex items-center gap-2 text-xs opacity-60">
                        <span>tokens≈{ffTokens ?? 0}</span>
                        {/* Decision chip rendered from latest WS decision */}
                        {(() => {
                          try {
                            const last = logs.find(l=> l.includes('dt_freeform_decision'));
                            if (!last) return null;
                            const json = JSON.parse(last.replace(/^\[[^\]]+\]\s*dt_freeform_decision:\s*/,'') || '{}');
                            const klass = String(json.class||'').toLowerCase();
                            const badge = klass.includes('major') ? 'badge-error' : klass.includes('minor') ? 'badge-warning' : klass.includes('behavior') ? 'badge-success' : 'badge-ghost';
                            const tip = `mask=${(json.mask||[]).join(', ')}, strategy=${json.strategy}, conf=${json.confidence}`;
                            return <span className={`badge ${badge}`} title={tip}>auto: {json.class||'—'}</span>;
                          } catch { return null; }
                        })()}
                      </div>
                    </div>
                    <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">{(() => {
                      const obj = ffPreview ?? currentDtConfig ?? {};
                      const s = JSON.stringify(obj, null, 2);
                      return s && s !== '{}' ? s : '—';
                    })()}</pre>
                    {ffNotes?.length > 0 && (
                      <div className="alert alert-warning text-xs">
                        <ul className="list-disc ml-4">
                          {ffNotes.map((n,i)=>(<li key={`${i}-${n}`}>{n}</li>))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              </div>)}
              {activeTab==='persona' && (
                <div className="flex gap-2 justify-end">
                  <button className="btn btn-sm" onClick={async()=>{ setFfStatus('queued'); setFfPreview(null); setFfNotes([]); setError(''); try { const r = await userService.dtFreeformPreview(freeform, initDataRaw); if (!r.success) setFfStatus('error'); } catch { setFfStatus('error'); } }}>Preview</button>
                  <button className={`btn btn-primary btn-sm ${ffStatus==='applying'?'loading':''}`} disabled={!freeform.trim() || !Object.values(applyMask).some(Boolean)} onClick={async()=>{ setFfStatus('applying'); setError(''); try { const r = await userService.dtFreeformApply({ content: freeform, apply_mask: applyMask, strategy }, initDataRaw); setFfStatus(r.success?'queued':'error'); } catch { setFfStatus('error'); } }}>Apply</button>
                  <button className="btn btn-accent btn-sm" disabled={!freeform.trim()} onClick={async()=>{ try { setFfStatus('applying'); setError(''); await userService.request(`/users/me/dt-config/freeform/auto-apply`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content: freeform, aggressiveness: 'balanced' }) }, initDataRaw); } catch (e) { setFfStatus('error'); } }}>Auto‑Apply</button>
                  <button className="btn btn-ghost btn-sm" onClick={async()=>{ try { const last = await userService.dtFreeformLast(initDataRaw); if (last.success) { const versions = (last.data?.dt_freeform?.versions||[]) as any[]; const lastId = versions?.slice(-1)[0]?.id; if (lastId) { await userService.dtFreeformRollback(lastId, initDataRaw); } } } catch {} }}>Rollback last</button>
                </div>
              )}
            </div>
          </div>
          )}

          {/* Persona editor (dt_config) – now visible under Alignment */}
          {activeTab==='alignment' && (
            <div className="card bg-base-200">
              <div className="card-body grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Suggestions header */}
                <div className="md:col-span-2">
                  <div className="alert alert-info text-sm">
                    <div>
                      <strong>Подсказки:</strong> добавьте в лексикон системные слова (паттерн, динамика), психологию (тень, проекция), прямой язык (разъеб). В Anti-Generic держите stop_phrases: ["погнали","давай сделаем","интересно,"] и включите anchors.require_min=1.
                  </div>
                  </div>
                </div>
                <div>
                  <div className="label text-sm opacity-70 mb-1">Имя персоны</div>
                  <input className="input input-bordered w-full" value={draftEdit.persona_name || ''} onChange={(e)=>setDraftEdit({...draftEdit, persona_name: e.target.value})} />
                </div>
                {/* Removed legacy style inputs to avoid duplication; tone/lexicon now under DT persona */}
                <div className="md:col-span-2">
                  <div className="label text-sm opacity-70 mb-1">Как AI будет писать черновики</div>
                  <textarea className="textarea textarea-bordered w-full min-h-24" value={draftEdit.style_prompt || ''} onChange={(e)=>{ setDraftEdit({...draftEdit, style_prompt: e.target.value}); if (hydratedRef.current) { const h = setTimeout(() => saveEdits(), 1200); (saveEdits as any)._t && clearTimeout((saveEdits as any)._t); (saveEdits as any)._t = h; } }} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Темы интересов" value={draftEdit.topics_of_interest || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, topics_of_interest: v})); }} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Шаблоны формулировок" value={draftEdit.signature_templates || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, signature_templates: v})); }} />
                </div>
                <div>
                  <TagInput label="Делать" value={draftEdit.do_list || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, do_list: v})); }} />
                </div>
                <div>
                  <TagInput label="Не делать" value={draftEdit.dont_list || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, dont_list: v})); }} />
                </div>
                <div>
                  <TagInput label="Приветствия" value={draftEdit.greetings || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, greetings: v})); }} />
                </div>
                <div>
                  <TagInput label="Типичные окончания" value={draftEdit.typical_endings || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, typical_endings: v})); }} />
                </div>
                <div className="md:col-span-2">
                  <TagInput label="Фирменные фразы" value={draftEdit.signature_phrases || []} onChange={(v)=>{ setDraftEdit((prev:any)=> ({...prev, signature_phrases: v})); }} />
                </div>
                {/* DT Config editable subset – tag-based */}
                <div className="md:col-span-2">
                  <h4 className="font-semibold mt-2">Digital Twin – Персона</h4>
                  <div className="label text-sm opacity-70 mb-1">Core Archetype</div>
                  <input className="input input-bordered w-full mb-2" value={draftEdit.dt_config?.persona?.core_archetype || ''} onChange={(e)=>{ setDraftEdit({...draftEdit, dt_config:{...draftEdit.dt_config, persona:{...(draftEdit.dt_config?.persona||{}), core_archetype:e.target.value}}}); if (hydratedRef.current) { const h = setTimeout(() => saveEdits(), 1200); (saveEdits as any)._t && clearTimeout((saveEdits as any)._t); (saveEdits as any)._t = h; } }} />
                  <div className="label text-sm opacity-70 mb-1">Talents</div>
                  <TagInput
                    label=""
                    value={(() => {
                      const t = (draftEdit.dt_config?.persona?.talents||[]) as any[];
                      return Array.isArray(t) ? t.map((x:any)=> typeof x === 'string' ? x : (x?.name || '')).filter(Boolean) : [];
                    })()}
                    onChange={(names)=>{
                      setDraftEdit((prev:any)=>{
                        const next = JSON.parse(JSON.stringify(prev||{}));
                        const arr = (names||[]).map((n:string)=> ({ name: n, weight: 1.0 }));
                        next.dt_config = next.dt_config || {};
                        next.dt_config.persona = next.dt_config.persona || {};
                        next.dt_config.persona.talents = arr;
                        return next;
                      })
                    }}
                  />
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                    <div>
                      <div className="label text-sm opacity-70 mb-1">Lexicon: system</div>
                      <TagInput label="" value={((draftEdit.dt_config?.persona?.voice?.lexicon?.system)||[])} onChange={(v)=>{
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev));
                          ensurePath(next,["dt_config","persona","voice","lexicon"],{});
                          next.dt_config.persona.voice.lexicon.system = v;
                          return next;
                        });
                      }} />
                    </div>
                    <div>
                      <div className="label text-sm opacity-70 mb-1">Lexicon: psychology</div>
                      <TagInput label="" value={((draftEdit.dt_config?.persona?.voice?.lexicon?.psychology)||[])} onChange={(v)=>{
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev));
                          ensurePath(next,["dt_config","persona","voice","lexicon"],{});
                          next.dt_config.persona.voice.lexicon.psychology = v;
                          return next;
                        });
                      }} />
                    </div>
                    <div>
                      <div className="label text-sm opacity-70 mb-1">Lexicon: direct</div>
                      <TagInput label="" value={((draftEdit.dt_config?.persona?.voice?.lexicon?.direct)||[])} onChange={(v)=>{
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev));
                          ensurePath(next,["dt_config","persona","voice","lexicon"],{});
                          next.dt_config.persona.voice.lexicon.direct = v;
                          return next;
                        });
                      }} />
                    </div>
                    <div>
                      <div className="label text-sm opacity-70 mb-1">Banned starters</div>
                      <TagInput label="" value={((draftEdit.dt_config?.persona?.voice?.banned_starters)||[])} onChange={(v)=>{
                        setDraftEdit((prev:any)=>{
                          const next = JSON.parse(JSON.stringify(prev));
                          ensurePath(next,["dt_config","persona","voice"],{});
                          next.dt_config.persona.voice.banned_starters = v;
                          return next;
                        });
                      }} />
                    </div>
                  </div>
                  <details className="mt-2">
                    <summary className="cursor-pointer text-sm opacity-70">Advanced (values JSON)</summary>
                    <textarea className="textarea textarea-bordered w-full min-h-20 mt-2" value={JSON.stringify(draftEdit.dt_config?.persona?.values || {}, null, 2)} onChange={(e)=>{ try { const v = JSON.parse(e.target.value||'{}'); setDraftEdit({...draftEdit, dt_config:{...draftEdit.dt_config, persona:{...(draftEdit.dt_config?.persona||{}), values:v}}}); if (hydratedRef.current) { const h = setTimeout(() => saveEdits(), 1200); (saveEdits as any)._t && clearTimeout((saveEdits as any)._t); (saveEdits as any)._t = h; } } catch {} }} />
                  </details>
                </div>

                <div className="md:col-span-2">
                  <h4 className="font-semibold mt-2">Sub‑personas (who speaks in which context)</h4>
                  <SubPersonaPanel
                    personas={draftEdit?.dt_config?.dynamic_filters?.sub_personalities || {}}
                    onChange={(next)=>{
                      setDraftEdit((prev:any)=>{
                        const copy = JSON.parse(JSON.stringify(prev||{}));
                        ensurePath(copy,["dt_config","dynamic_filters"],{});
                        copy.dt_config.dynamic_filters.sub_personalities = next;
                        return copy;
                      })
                    }}
                    onPreview={async (text:string)=>{
                      try { const res = await userService.subPersonaClassifyPreview(text, initDataRaw); return res.success ? (res.data as any) : null; } catch { return null; }
                    }}
                  />
                </div>

                <div className="md:col-span-2">
                  <h4 className="font-semibold mt-2">Digital Twin – Генерация</h4>
                  <div className="label text-sm opacity-70 mb-1 flex items-center gap-2">Anti-Generic: Stop phrases <InfoTip text="Если черновик начинается с любого из этих выражений — мы вырежем или перегенерим. Борется с шаблонностью (например, ‘погнали’, ‘давай сделаем’)." /></div>
                  <TagInput label="" value={((draftEdit.dt_config?.anti_generic?.stop_phrases)||[])} onChange={(v)=>{
                    setDraftEdit((prev:any)=>{
                      const next = JSON.parse(JSON.stringify(prev));
                      ensurePath(next,["dt_config","anti_generic"],{});
                      next.dt_config.anti_generic.stop_phrases = v;
                      return next;
                    });
                  }} />
                  <div className="label text-sm opacity-70 mb-1 mt-2 flex items-center gap-2">Anchors: types <InfoTip text="Что конкретно нужно процитировать из поста минимум один раз (claim/number/named entity/quote fragment). Заземляет комментарий в исходном тексте." /></div>
                  <TagInput label="" value={((draftEdit.dt_config?.generation_controls?.anchors?.types)||[])} onChange={(v)=>{
                    setDraftEdit((prev:any)=>{
                      const next = JSON.parse(JSON.stringify(prev));
                      ensurePath(next,["dt_config","generation_controls","anchors"],{});
                      next.dt_config.generation_controls.anchors.types = v;
                      return next;
                    });
                  }} />
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="card bg-base-100">
                      <div className="card-body gap-3">
                        <div className="flex items-center gap-2"><h5 className="font-semibold text-sm">Decoding</h5><InfoTip text="Контролирует разнообразие и риск: чем выше Temperature и Top‑P, тем дерзче формулировки и шире выбор слов." /></div>
                        <label className="label-text text-xs flex items-center gap-2">Temperature <InfoTip text="0.0 — максимально предсказуемо, 1.0 — свободно и рискованно." /></label>
                        <input type="range" min={0} max={1} step={0.01} className="range range-xs"
                          value={Number(draftEdit.dt_config?.decoding?.temperature ?? 0.4)}
                          onChange={(e)=>{
                            const val = Number(e.target.value);
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","decoding"],{});
                            next.dt_config.decoding.temperature = val;
                            setDraftEdit(next);
                          }} />
                        <label className="label-text text-xs flex items-center gap-2">Top P <InfoTip text="Сэмплинг по вероятностной массе. Меньше — сдержаннее, больше — разнообразнее." /></label>
                        <input type="range" min={0} max={1} step={0.01} className="range range-xs"
                          value={Number(draftEdit.dt_config?.decoding?.top_p ?? 0.9)}
                          onChange={(e)=>{
                            const val = Number(e.target.value);
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","decoding"],{});
                            next.dt_config.decoding.top_p = val;
                            setDraftEdit(next);
                          }} />
                        <label className="label cursor-pointer justify-start gap-2 text-xs">
                          <input type="checkbox" className="toggle toggle-xs"
                            checked={Boolean(draftEdit.dt_config?.anti_generic?.ban_openers ?? true)}
                            onChange={(e)=>{
                              const next = JSON.parse(JSON.stringify(draftEdit||{}));
                              ensurePath(next,["dt_config","anti_generic"],{});
                              next.dt_config.anti_generic.ban_openers = e.target.checked;
                              setDraftEdit(next);
                            }} />
                          <span className="flex items-center gap-2">Ban generic openers <InfoTip text="Режет типовые вступления типа ‘погнали/давай сделаем’." /></span>
                        </label>
                      </div>
                    </div>

                    <div className="card bg-base-100">
                      <div className="card-body gap-3">
                        <div className="flex items-center gap-2"><h5 className="font-semibold text-sm">Generation controls</h5><InfoTip text="Сколько вариантов генерировать и как звучать: длина, доля вопросов, структура." /></div>
                        <label className="label-text text-xs flex items-center gap-2">Candidates <InfoTip text="Количество альтернатив на один пост. Больше — дороже и дольше." /></label>
                        <input type="number" min={1} max={3} className="input input-bordered input-xs w-24"
                          value={Number(draftEdit.dt_config?.generation_controls?.num_candidates ?? 1)}
                          onChange={(e)=>{
                            const val = Math.max(1, Math.min(3, Number(e.target.value||1)));
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","generation_controls"],{});
                            next.dt_config.generation_controls.num_candidates = val;
                            setDraftEdit(next);
                          }} />
                        <label className="label-text text-xs flex items-center gap-2">Length (min–max chars) <InfoTip text="Целевой коридор длины комментария. Слишком длинные будут подрезаны." /></label>
                        <div className="flex items-center gap-2">
                          <input type="number" className="input input-bordered input-xs w-20" placeholder="80"
                            value={Number((draftEdit.dt_config?.generation_controls?.length?.char_target||[80,180])[0])}
                            onChange={(e)=>{
                              const val = Number(e.target.value||80);
                              const next = JSON.parse(JSON.stringify(draftEdit||{}));
                              ensurePath(next,["dt_config","generation_controls","length"],{});
                              const cur = next.dt_config.generation_controls.length.char_target || [80,180];
                              cur[0] = val; next.dt_config.generation_controls.length.char_target = cur; setDraftEdit(next);
                            }} />
                          <span className="text-xs">—</span>
                          <input type="number" className="input input-bordered input-xs w-20" placeholder="180"
                            value={Number((draftEdit.dt_config?.generation_controls?.length?.char_target||[80,180])[1])}
                            onChange={(e)=>{
                              const val = Number(e.target.value||180);
                              const next = JSON.parse(JSON.stringify(draftEdit||{}));
                              ensurePath(next,["dt_config","generation_controls","length"],{});
                              const cur = next.dt_config.generation_controls.length.char_target || [80,180];
                              cur[1] = val; next.dt_config.generation_controls.length.char_target = cur; setDraftEdit(next);
                            }} />
                        </div>
                        <label className="label-text text-xs flex items-center gap-2">Question ratio target <InfoTip text="Как часто заканчивать вопросом. Полезно для провокации диалога." /></label>
                        <input type="range" min={0} max={1} step={0.05} className="range range-xs"
                          value={Number(draftEdit.dt_config?.generation_controls?.rhetoric?.question_ratio_target ?? 0.6)}
                          onChange={(e)=>{
                            const val = Number(e.target.value);
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","generation_controls","rhetoric"],{});
                            next.dt_config.generation_controls.rhetoric.question_ratio_target = val;
                            setDraftEdit(next);
                          }} />
                      </div>
                    </div>

                    <div className="card bg-base-100">
                      <div className="card-body gap-3">
                        <div className="flex items-center gap-2"><h5 className="font-semibold text-sm">Style metrics</h5><InfoTip text="Ограничители стиля: эмодзи, восклицания, формальность. Держим ровный, точный тон." /></div>
                        <label className="label-text text-xs flex items-center gap-2">Max emoji ratio <InfoTip text="Максимальная доля эмодзи в тексте. Держим минимально, чтобы не казаться пластиком." /></label>
                        <input type="range" min={0} max={0.2} step={0.005} className="range range-xs"
                          value={Number(draftEdit.dt_config?.style_metrics?.emoji_cap_ratio ?? 0.02)}
                          onChange={(e)=>{
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","style_metrics"],{});
                            next.dt_config.style_metrics.emoji_cap_ratio = Number(e.target.value);
                            setDraftEdit(next);
                          }} />
                        <label className="label-text text-xs flex items-center gap-2">Allow exclamation <InfoTip text="Сколько восклицаний допустимо. 0 — без истерик, 1–3 — точечные акценты." /></label>
                        <input type="range" min={0} max={3} step={1} className="range range-xs"
                          value={Number(draftEdit.dt_config?.style_metrics?.punctuation?.allow_exclaim ?? 0)}
                          onChange={(e)=>{
                            const next = JSON.parse(JSON.stringify(draftEdit||{}));
                            ensurePath(next,["dt_config","style_metrics","punctuation"],{});
                            next.dt_config.style_metrics.punctuation.allow_exclaim = Number(e.target.value);
                            setDraftEdit(next);
                          }} />
                        <label className="label cursor-pointer justify-start gap-2 text-xs">
                          <input type="checkbox" className="toggle toggle-xs"
                            checked={Boolean(draftEdit.dt_config?.anti_generic?.reroll_if_banned ?? true)}
                            onChange={(e)=>{
                              const next = JSON.parse(JSON.stringify(draftEdit||{}));
                              ensurePath(next,["dt_config","anti_generic"],{});
                              next.dt_config.anti_generic.reroll_if_banned = e.target.checked;
                              setDraftEdit(next);
                            }} />
                          <span className="flex items-center gap-2">Re‑roll if banned <InfoTip text="Если старт попадает в стоп‑фразу — автоматически перегенерируем." /></span>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="md:col-span-2 flex justify-end gap-2">
                  <button className={`btn btn-primary ${isSaving ? 'loading' : ''}`} onClick={saveEdits} disabled={isSaving}>Сохранить</button>
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
          {activeTab==='analyze' && (
          <div className="card-actions justify-center">
            <button 
              className={`btn btn-primary ${isAnalyzing ? 'loading' : ''}`}
              onClick={handleAnalyzeContext}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? 'Анализирую...' : '🔍 Анализировать Контекст'}
            </button>
          </div>
          )}

          {/* Sub-persona Test */}
          {activeTab==='learning' && (
          <div className="card bg-base-200">
            <div className="card-body gap-2">
              <h4 className="font-semibold">Learning</h4>
              <p className="text-xs opacity-70">После того как черновики одобрены/отправлены, улучшайте профиль:</p>
              <div className="flex flex-wrap gap-2 text-xs">
                <button className="btn btn-xs" onClick={()=>{ window.location.href = '/app'; }}>Go to drafts</button>
                <button className="btn btn-xs btn-ghost" onClick={()=>{ /* placeholder for nightly toggle wiring */ }}>Nightly learning (coming soon)</button>
              </div>
              </div>
            </div>
          )}

          {activeTab==='analyze' && analysisResult && (
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