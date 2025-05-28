export enum TelegramMessengerChatType {
  PRIVATE = 'private',
  GROUP = 'group',
  SUPERGROUP = 'supergroup',
  CHANNEL = 'channel'
}

export interface TelegramChat {
  id: string;
  telegram_id: number;
  user_id: string;
  type: TelegramMessengerChatType;
  title: string | null;
  member_count: number | null;
}

export interface ChatListResponse {
  chats: TelegramChat[];
}

export interface TelegramMessage {
  id: string;
  telegram_id: number;
  chat_id: string;
  sender_id: string | null;
  text: string | null;
  date: string; // ISO formatted datetime
  edit_date: string | null; // ISO formatted datetime
  media_type: string | null;
  file_id: string | null;
  reply_to_message_telegram_id: number | null;
}

export interface ChatMessagesResponse {
  messages: TelegramMessage[];
}

export interface TelegramChatUser {
  id: string;
  telegram_id: number;
  user_id: string;
  chat_id: string;
  management_person_id: string | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  phone: string | null;
  is_bot: boolean;
  is_admin: boolean;
  is_creator: boolean;
  join_date: string | null; // ISO formatted datetime
}

export interface ChatParticipantsResponse {
  participants: TelegramChatUser[];
}

export interface Chat {
  id: number;
  type: string;
  title?: string;
  username?: string;
  first_name?: string;
  last_name?: string;
  photo?: {
    small_file_id: string;
    big_file_id: string;
  };
  description?: string;
  invite_link?: string;
  pinned_message?: any;
  permissions?: {
    can_send_messages?: boolean;
    can_send_media_messages?: boolean;
    can_send_polls?: boolean;
    can_send_other_messages?: boolean;
    can_add_web_page_previews?: boolean;
    can_change_info?: boolean;
    can_invite_users?: boolean;
    can_pin_messages?: boolean;
  };
  slow_mode_delay?: number;
  message_auto_delete_time?: number;
  has_protected_content?: boolean;
  sticker_set_name?: string;
  can_set_sticker_set?: boolean;
  linked_chat_id?: number;
  location?: {
    location: {
      longitude: number;
      latitude: number;
    };
    address: string;
  };
} 