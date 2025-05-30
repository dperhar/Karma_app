import { AIRequestModel } from '@/core/api/models/ai-models';

// AI Request types
export interface AIRequestBase {
  request_text: string;
  model: AIRequestModel;
}

export interface AIRequestCreate extends AIRequestBase {
  dialog_id: string;
  user_id: string;
}

export interface AIRequestResponse extends AIRequestBase {
  id: string;
  dialog_id: string;
  user_id: string;
  response_text: string;
  created_at: string;
  updated_at: string;
}

// AI Dialog types
export interface AIDialogBase {
  title?: string;
}

export interface AIDialogCreate {
  chat_id: string;
  user_id: string;
}

export interface AIDialogResponse {
  id: string;
  chat_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

// AI Dialog Message types
export interface AIDialogMessageCreate {
  dialog_id: string;
  content: string;
  role: 'user' | 'assistant';
  model?: string;
}

export interface AIDialogMessageResponse {
  id: string;
  dialog_id: string;
  content: string;
  role: string;
  model?: string;
  created_at: string;
  updated_at: string;
}

export interface AIDialogWithMessages {
  dialog: AIDialogResponse;
  messages: AIDialogMessageResponse[];
}

export interface LangChainMessageRequest {
  dialog_id: string;
  content: string;
  dialog_context_length?: number;
  model_name?: string;
  provider?: string;
  temperature?: number;
  prompt_template?: string;
  max_tokens?: number;
} 