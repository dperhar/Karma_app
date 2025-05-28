import { format } from 'date-fns';
import { FC, useState } from 'react';

import { AIDialogMessageResponse } from '@/types/ai';

interface AIMessageProps {
  message: AIDialogMessageResponse;
}

export const AIMessage: FC<AIMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';
  const formattedTime = format(new Date(message.created_at), 'HH:mm');
  const [isCopied, setIsCopied] = useState(false);
  
  // Функция копирования сообщения в буфер обмена
  const copyToClipboard = () => {
    navigator.clipboard.writeText(message.content)
      .then(() => {
        // Показываем индикатор успешного копирования
        setIsCopied(true);
        // Сбрасываем статус через 2 секунды
        setTimeout(() => setIsCopied(false), 2000);
      })
      .catch(err => {
        console.error('Не удалось скопировать текст: ', err);
      });
  };
  
  return (
    <div className={`chat ${isUser ? 'chat-end' : 'chat-start'} mb-4`}>
      <div className="chat-header flex items-center justify-between w-full">
        <div className="flex items-center">
          <span className="font-medium">{isUser ? 'You' : 'AI Assistant'}</span>
          <time className="text-xs opacity-50 ml-1">{formattedTime}</time>
        </div>
        
        <button 
          onClick={copyToClipboard}
          className="btn btn-xs btn-ghost opacity-50 hover:opacity-100"
          title="Копировать сообщение"
        >
          {isCopied ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-success" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M8 2a1 1 0 000 2h2a1 1 0 100-2H8z" />
              <path d="M3 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v6h-4.586l1.293-1.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L10.414 13H15v3a2 2 0 01-2 2H5a2 2 0 01-2-2V5zM15 11h2a1 1 0 110 2h-2v-2z" />
            </svg>
          )}
        </button>
      </div>
      
      <div className={`chat-bubble ${isUser ? 'chat-bubble-primary' : 'chat-bubble-secondary'} whitespace-pre-wrap`}>
        {message.content}
      </div>
      
      {/* Информация о модели (только для сообщений ассистента) */}
      {!isUser && message.model && (
        <div className="chat-footer opacity-50 text-xs mt-1">
          <span className="bg-base-300 px-2 py-1 rounded">Model: {message.model}</span>
        </div>
      )}
    </div>
  );
}; 