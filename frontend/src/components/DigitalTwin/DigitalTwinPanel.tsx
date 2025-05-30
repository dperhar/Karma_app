'use client';

import React, { useState } from 'react';
import { userService } from '@/core/api/services/user-service';
import { User } from '@/types/user';
import { initData, useSignal } from '@telegram-apps/sdk-react';

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
  const initDataRaw = useSignal(initData.raw);

  const handleAnalyzeContext = async () => {
    if (isAnalyzing) return;
    
    setIsAnalyzing(true);
    setError('');
    setAnalysisResult('');

    try {
      console.log('Starting context analysis...');
      const response = await userService.analyzeUserContext(initDataRaw);
      
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
            const userResponse = await userService.getCurrentUser(initDataRaw);
            if (userResponse.success && userResponse.data) {
              onUserUpdate(userResponse.data);
            }
          } catch (e) {
            console.error('Failed to refresh user data:', e);
          }
        }
      } else {
        setError(response.error || 'Неизвестная ошибка');
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