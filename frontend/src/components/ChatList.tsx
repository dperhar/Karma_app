import { TelegramChat } from '@/types/chat';
import { ChatItem } from './ChatItem';

interface ChatListProps {
  chats: TelegramChat[];
  onChatClick?: (chat: TelegramChat) => void;
  isLoading?: boolean;
  selectedChat?: TelegramChat | null;
}

export const ChatList = ({ 
  chats, 
  onChatClick, 
  isLoading, 
  selectedChat 
}: ChatListProps) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-6">
        <span className="loading loading-spinner loading-md text-primary"></span>
        <span className="ml-3 text-base-content text-opacity-70">Loading chats...</span>
      </div>
    );
  }

  if (!chats || chats.length === 0) {
    return (
      <div className="card bg-base-200 p-6">
        <div className="text-center">
          <div className="flex justify-center mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-base-content text-opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p className="text-base-content text-opacity-60">No chats available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {chats.map((chat) => (
        <ChatItem 
          key={chat.id} 
          chat={chat} 
          onClick={onChatClick}
          isSelected={selectedChat?.id === chat.id}
        />
      ))}
    </div>
  );
}; 