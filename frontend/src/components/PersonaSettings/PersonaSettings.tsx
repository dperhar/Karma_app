'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ApiClient } from '@/core/api/api-client';
import { APIResponse } from '@/types/api';

interface PersonaData {
  persona_name?: string;
  persona_style_description?: string;
  persona_interests_json?: string[];
  preferred_ai_model?: string;
}

interface PersonaSettingsProps {
  initDataRaw: string | null;
  onClose?: () => void;
}

class UserAPI extends ApiClient {
  async getPersona(initDataRaw: string): Promise<APIResponse<PersonaData>> {
    return this.request<APIResponse<PersonaData>>('/user/persona', {
      method: 'GET',
    }, initDataRaw);
  }

  async updatePersona(data: PersonaData, initDataRaw: string): Promise<APIResponse<PersonaData>> {
    return this.request<APIResponse<PersonaData>>('/user/persona', {
      method: 'PUT',
      body: JSON.stringify(data),
    }, initDataRaw);
  }
}

const userAPI = new UserAPI();

export const PersonaSettings: React.FC<PersonaSettingsProps> = ({
  initDataRaw,
  onClose,
}) => {
  const [persona, setPersona] = useState<PersonaData>({
    persona_name: '',
    persona_style_description: '',
    persona_interests_json: [],
    preferred_ai_model: 'gpt-4.1-mini'
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newInterest, setNewInterest] = useState('');

  // Загружаем текущие настройки персоны
  useEffect(() => {
    if (initDataRaw) {
      loadPersona();
    }
  }, [initDataRaw]);

  const loadPersona = async () => {
    if (!initDataRaw) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await userAPI.getPersona(initDataRaw);
      
      if (response.success && response.data) {
        setPersona({
          persona_name: response.data.persona_name || '',
          persona_style_description: response.data.persona_style_description || '',
          persona_interests_json: response.data.persona_interests_json || [],
          preferred_ai_model: response.data.preferred_ai_model || 'gpt-4.1-mini'
        });
      }
    } catch (error: any) {
      console.error('Error loading persona:', error);
      setError(error.message || 'Failed to load persona settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!initDataRaw) return;
    
    setIsSaving(true);
    setError(null);
    
    try {
      const response = await userAPI.updatePersona(persona, initDataRaw);
      
      if (response.success) {
        console.log('Persona updated successfully');
        onClose?.();
      } else {
        throw new Error(response.message || 'Failed to update persona');
      }
    } catch (error: any) {
      console.error('Error saving persona:', error);
      setError(error.message || 'Failed to save persona settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddInterest = () => {
    if (newInterest.trim() && !persona.persona_interests_json?.includes(newInterest.trim())) {
      setPersona(prev => ({
        ...prev,
        persona_interests_json: [...(prev.persona_interests_json || []), newInterest.trim()]
      }));
      setNewInterest('');
    }
  };

  const handleRemoveInterest = (index: number) => {
    setPersona(prev => ({
      ...prev,
      persona_interests_json: prev.persona_interests_json?.filter((_, i) => i !== index) || []
    }));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddInterest();
    }
  };

  if (!initDataRaw) {
    return (
      <div className="p-6 text-center">
        <p className="text-muted-foreground">Authentication required to access persona settings</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">AI Persona Settings</h2>
          <p className="text-muted-foreground">Configure your AI comment generation persona</p>
        </div>
        {onClose && (
          <Button variant="ghost" onClick={onClose}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        )}
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 bg-red-100 border border-red-300 rounded-md">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <svg className="animate-spin h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Persona Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Persona Name</label>
            <input
              type="text"
              value={persona.persona_name}
              onChange={(e) => setPersona(prev => ({ ...prev, persona_name: e.target.value }))}
              className="w-full p-3 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g. Mark Zuckerberg, Elon Musk, Steve Jobs..."
            />
            <p className="text-xs text-muted-foreground">
              The name of the persona you want to emulate in comments
            </p>
          </div>

          {/* Style Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Communication Style</label>
            <textarea
              value={persona.persona_style_description}
              onChange={(e) => setPersona(prev => ({ ...prev, persona_style_description: e.target.value }))}
              className="w-full h-32 p-3 border border-border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Describe how this persona communicates: tone, style, key phrases, approach to topics..."
            />
            <p className="text-xs text-muted-foreground">
              Detailed description of the persona&apos;s communication style and approach
            </p>
          </div>

          {/* AI Model Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">AI Model</label>
            <select
              value={persona.preferred_ai_model}
              onChange={(e) => setPersona(prev => ({ ...prev, preferred_ai_model: e.target.value }))}
              className="w-full p-3 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="gpt-4.1-mini">GPT-4.1 Mini (Fast)</option>
              <option value="gpt-4">GPT-4 (Balanced)</option>
              <option value="gemini-pro">Gemini Pro</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
            </select>
            <p className="text-xs text-muted-foreground">
              Select the AI model for comment generation
            </p>
          </div>

          {/* Interests */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Interests & Keywords</label>
            
            {/* Add new interest */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newInterest}
                onChange={(e) => setNewInterest(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 p-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Add interest or keyword..."
              />
              <Button onClick={handleAddInterest} disabled={!newInterest.trim()}>
                Add
              </Button>
            </div>

            {/* Interests list */}
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {persona.persona_interests_json && persona.persona_interests_json.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {persona.persona_interests_json.map((interest, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-1 bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm"
                    >
                      <span>{interest}</span>
                      <button
                        onClick={() => handleRemoveInterest(index)}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">No interests added yet</p>
              )}
            </div>
            
            <p className="text-xs text-muted-foreground">
              AI will only generate comments for posts related to these interests
            </p>
          </div>

          {/* Example Interests */}
          <div className="p-4 bg-blue-50 rounded-md">
            <h4 className="text-sm font-medium mb-2">Example interests for tech personas:</h4>
            <div className="flex flex-wrap gap-1">
              {['AI', 'Machine Learning', 'Blockchain', 'VR', 'AR', 'Metaverse', 'Startup', 'Technology', 'Innovation', 'Web3'].map((example) => (
                <button
                  key={example}
                  onClick={() => {
                    if (!persona.persona_interests_json?.includes(example)) {
                      setPersona(prev => ({
                        ...prev,
                        persona_interests_json: [...(prev.persona_interests_json || []), example]
                      }));
                    }
                  }}
                  className="text-xs bg-white border border-blue-200 text-blue-700 px-2 py-1 rounded hover:bg-blue-100 transition-colors"
                >
                  + {example}
                </button>
              ))}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex gap-2 pt-4 border-t">
            <Button onClick={handleSave} disabled={isSaving} className="bg-primary hover:bg-primary/90">
              {isSaving ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Saving...
                </>
              ) : (
                'Save Persona Settings'
              )}
            </Button>
            {onClose && (
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}; 