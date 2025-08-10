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

  const initDataRaw = 'mock_init_data_for_telethon';
  const { lastMessage, isConnected } = useWebSocket({ userId: user.id, initDataRaw });

  // On mount, fetch AI profile once to hydrate status if backend already saved earlier
  useEffect(() => {
    (async () => {
      try {
        const aiProfile = await userService.getMyAIProfile(initDataRaw);
        if (aiProfile.success && aiProfile.data && onUserUpdate) {
          onUserUpdate({
            ...user,
            context_analysis_status: aiProfile.data.analysis_status ?? user.context_analysis_status,
            last_context_analysis_at: aiProfile.data.last_analyzed_at ?? user.last_context_analysis_at,
            persona_name: aiProfile.data.persona_name ?? user.persona_name,
          } as any);
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
            }
          } catch {}
        } catch {}
      })();
    }
    if (lastMessage.event === 'vibe_profile_failed') {
      setIsAnalyzing(false);
      setError(lastMessage.data?.error || 'Анализ не удался');
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