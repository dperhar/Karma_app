"use client";
import React, { useEffect, useMemo } from 'react';
import { useAISettingsStore, modelCapabilities } from '@/store/aiSettingsStore';
import { Button } from './Button/Button';
import { userService } from '@/core/api/services/user-service';

type Option = { label: string; value: string };

const MODELS: Option[] = [
  { label: 'Gemini 2.5 Pro', value: 'gemini-2.5-pro' },
  { label: 'Gemini 2.0 Flash Lite', value: 'gemini-2.0-flash-lite' },
  { label: 'Gemini 1.5 Pro', value: 'gemini-1.5-pro' },
];

export const AIControlSidebar: React.FC = () => {
  const { settings, setSettings, tokensUsedApprox, dailyTokenCap, setCap } = useAISettingsStore();

  const caps = useMemo(() => modelCapabilities[settings.model], [settings.model]);
  const progress = Math.min(100, Math.floor((tokensUsedApprox / Math.max(1, dailyTokenCap)) * 100));

  useEffect(() => {
    (async () => {
      try {
        // Ensure session is established before fetching AI settings
        const me = await userService.getCurrentUser();
        if (!me?.success || !me?.data?.id) return;

        const res = await userService.getAISettings();
        if (res?.success && res?.data) {
          setSettings({
            model: (res.data.model || 'gemini-2.5-pro') as any,
            temperature: typeof res.data.temperature === 'number' ? res.data.temperature : 0.2,
            maxOutputTokens: typeof res.data.max_output_tokens === 'number' ? res.data.max_output_tokens : 512,
            provider: (res.data.provider === 'proxy' ? 'proxy' : 'google') as any,
          });
        }
      } catch (e) {
        // ignore (e.g., 401 during early mount)
      }
    })();
  }, [setSettings]);

  const persist = async (patch: Partial<{ model: string; temperature: number; max_output_tokens: number; provider: 'google' | 'proxy' }>) => {
    try {
      await userService.updateAISettings({
        model: patch.model,
        temperature: patch.temperature,
        max_output_tokens: patch.max_output_tokens,
        provider: patch.provider,
      });
    } catch (e) {
      // ignore for now
    }
  };

  return (
    <aside className="fixed left-0 top-12 bottom-0 w-72 bg-black/30 backdrop-blur-md border-r border-white/10 p-4 z-40 overflow-y-auto">
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-gray-200">AI Controls</h3>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Model</label>
          <select
            value={settings.model}
            onChange={async (e) => {
              const v = e.target.value as any;
              setSettings({ model: v });
              await persist({ model: v });
            }}
            className="w-full rounded border border-white/10 bg-black/20 text-gray-100 p-2 text-sm"
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value} className="bg-white dark:bg-gray-900">
                {m.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-400 mb-1">Fallbacks</label>
          <div className="flex gap-2">
            <button
              className={`px-2 py-1 rounded text-sm ${!(settings as any).enableFallbacks ? 'bg-blue-600 text-white' : 'bg-black/20 border border-white/10 text-gray-200'}`}
              onClick={async () => {
                setSettings({ ...(settings as any), enableFallbacks: false } as any);
                await persist({} as any);
              }}
            >
              Off
            </button>
            <button
              className={`px-2 py-1 rounded text-sm ${(settings as any).enableFallbacks ? 'bg-blue-600 text-white' : 'bg-black/20 border border-white/10 text-gray-200'}`}
              onClick={async () => {
                setSettings({ ...(settings as any), enableFallbacks: true } as any);
                await persist({} as any);
              }}
            >
              On
            </button>
          </div>
          <p className="text-[10px] text-gray-500 mt-1">Use proxy alternates if preferred model is unavailable.</p>
        </div>

        {caps.supportsTemperature && (
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Temperature <span className="text-gray-400">({settings.temperature.toFixed(2)})</span>
            </label>
            <input
              type="range"
              min={0}
              max={2}
              step={0.05}
              value={settings.temperature}
              onChange={async (e) => {
                const val = parseFloat(e.target.value);
                setSettings({ temperature: val });
                await persist({ temperature: val });
              }}
              className="w-full"
            />
          </div>
        )}

        {caps.supportsMaxTokens && (
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Max output tokens <span className="text-gray-400">({settings.maxOutputTokens})</span>
            </label>
            <input
              type="range"
              min={64}
              max={8192}
              step={64}
              value={settings.maxOutputTokens}
              onChange={async (e) => {
                const val = parseInt(e.target.value, 10);
                setSettings({ maxOutputTokens: val });
                await persist({ max_output_tokens: val });
              }}
              className="w-full"
            />
          </div>
        )}

        <div>
          <label className="block text-xs text-gray-400 mb-1">Provider</label>
          <div className="flex gap-2">
            <button
              className={`px-2 py-1 rounded text-sm ${settings.provider === 'google' ? 'bg-blue-600 text-white' : 'bg-black/20 border border-white/10 text-gray-200'}`}
              onClick={async () => {
                setSettings({ provider: 'google' as any });
                await persist({ provider: 'google' });
              }}
            >
              Google
            </button>
            <button
              className={`px-2 py-1 rounded text-sm ${settings.provider === 'proxy' ? 'bg-blue-600 text-white' : 'bg-black/20 border border-white/10 text-gray-200'}`}
              onClick={async () => {
                setSettings({ provider: 'proxy' as any });
                await persist({ provider: 'proxy' });
              }}
            >
              Proxy
            </button>
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Daily token cap</label>
          <input
            type="number"
            value={dailyTokenCap}
            onChange={(e) => setCap(parseInt(e.target.value || '0', 10))}
            className="w-full rounded border border-white/10 bg-black/20 text-gray-100 p-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Tokens used (approx)</label>
          <div className="w-full h-2 bg-white/10 rounded">
            <div
              className="h-2 bg-blue-500 rounded"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="text-xs text-gray-400 mt-1">{tokensUsedApprox} / {dailyTokenCap}</div>
        </div>

        <div className="flex gap-2 pt-2" />
      </div>
    </aside>
  );
};


