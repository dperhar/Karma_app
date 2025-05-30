export interface User {
  id: string;
  username: string;
  first_name: string;
  last_name?: string;
  email: string | null;
  telegram_id: number;
  telegram_session_string?: string | null;
  has_valid_tg_session?: boolean;
  last_telegram_auth_at?: string | null;
  telegram_chats_load_limit: number | null;
  telegram_messages_load_limit: number | null;
  preferred_ai_model: string | null;
  preferred_message_context_size: number | null;
  
  // Digital Twin fields
  persona_name?: string | null;
  persona_style_description?: string | null;
  persona_interests_json?: string | null;
  user_system_prompt?: string | null;
  last_context_analysis_at?: string | null;
  context_analysis_status?: string | null;
}

export interface UserResponse {
  user: User;
  success: boolean;
  message: string | null;
}


export interface UserUpdate {
  username?: string;
  first_name?: string;
  last_name?: string;
  email?: string | null;
  telegram_chats_load_limit?: number | null;
  telegram_messages_load_limit?: number | null;
  preferred_ai_model?: string | null;
  preferred_message_context_size?: number | null;
  
  // Digital Twin fields
  persona_name?: string | null;
  persona_style_description?: string | null;
  persona_interests_json?: string | null;
}

export enum AIModel {
  GPT_4_1 = "gpt-4.1",
  GPT_4_1_MINI = "gpt-4.1-mini",
  GPT_4_1_NANO = "gpt-4.1-nano",
  CLAUDE_3_7_SONNET = "claude-3-7-sonnet-20250219",
  CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
} 