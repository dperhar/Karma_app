import { create } from 'zustand';

type ModelKey = 'gpt-5' | 'gemini-2.5-pro' | 'gemini-1.5-flash' | 'claude-opus-4';

export type AISettings = {
  model: ModelKey;
  temperature: number;
  maxOutputTokens: number;
  provider?: 'google' | 'proxy';
};

type AISettingsState = {
  settings: AISettings;
  tokensUsedApprox: number;
  dailyTokenCap: number; // UI cap for progress bar
  setSettings: (s: Partial<AISettings>) => void;
  setUsage: (used: number) => void;
  setCap: (cap: number) => void;
};

export const useAISettingsStore = create<AISettingsState>((set) => ({
  settings: {
    model: 'gemini-2.5-pro',
    temperature: 0.2,
    maxOutputTokens: 512,
    provider: 'google',
  },
  tokensUsedApprox: 0,
  dailyTokenCap: 100000, // default session cap
  setSettings: (s) =>
    set((st) => ({ settings: { ...st.settings, ...s } })),
  setUsage: (used) => set(() => ({ tokensUsedApprox: used })),
  setCap: (cap) => set(() => ({ dailyTokenCap: cap })),
}));

export const modelCapabilities: Record<ModelKey, { supportsTemperature: boolean; supportsMaxTokens: boolean }> = {
  'gpt-5': { supportsTemperature: true, supportsMaxTokens: true },
  'gemini-2.5-pro': { supportsTemperature: true, supportsMaxTokens: true },
  'claude-opus-4': { supportsTemperature: true, supportsMaxTokens: true },
};


