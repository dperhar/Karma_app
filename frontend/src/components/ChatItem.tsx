import { TelegramChat, TelegramMessengerChatType } from '@/types/chat';

interface ChatItemProps {
  chat: TelegramChat;
  onClick?: (chat: TelegramChat) => void;
  isSelected?: boolean;
}

export const ChatItem = ({ chat, onClick, isSelected }: ChatItemProps) => {
  // Function to get icon based on chat type
  const getChatIcon = (type: TelegramMessengerChatType) => {
    switch (type) {
      case TelegramMessengerChatType.PRIVATE:
        return '👤';
      case TelegramMessengerChatType.GROUP:
        return '👥';
      case TelegramMessengerChatType.SUPERGROUP:
        return '🌐';
      case TelegramMessengerChatType.CHANNEL:
        return '📢';
      default:
        return '💬';
    }
  };

  const handleClick = () => {
    if (onClick) {
      onClick(chat);
    }
  };

  return (
    <div 
      className={`card card-compact card-bordered cursor-pointer transition-colors ${
        isSelected 
          ? 'bg-primary bg-opacity-10 border-primary' 
          : 'bg-base-200 hover:bg-base-300 border-base-300'
      }`}
      onClick={handleClick}
    >
      <div className="card-body flex-row items-center py-3 px-4">
        <div className="avatar placeholder mr-3">
          <div className="bg-neutral text-neutral-content rounded-full w-10 h-10 flex items-center justify-center">
            <span className="text-xl">{getChatIcon(chat.type)}</span>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-base-content truncate">
            {chat.title || `Chat ${chat.telegram_id}`}
          </h3>
          <p className="text-sm text-base-content text-opacity-70 flex items-center">
            <span className="badge badge-sm mr-2">
              {chat.type.charAt(0).toUpperCase() + chat.type.slice(1)}
            </span>
            {chat.member_count && (
              <span className="flex items-center text-xs">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                {chat.member_count}
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}; 