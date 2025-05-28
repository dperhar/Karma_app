import { useEffect, useRef, useState } from 'react';
import { useCommentStore } from '@/store/commentStore';

interface WebSocketMessage {
  event: string;
  data: any;
  user_id?: string;
}

interface UseWebSocketProps {
  userId?: string;
  initDataRaw?: string | null;
}

export const useWebSocket = ({ userId, initDataRaw }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  const { setCurrentDraft, fetchDrafts } = useCommentStore();

  const connect = () => {
    if (!userId || !initDataRaw) {
      console.log('Missing userId or initDataRaw for WebSocket connection');
      return;
    }

    try {
      // WebSocket URL - adjust according to your backend configuration
      const wsUrl = `ws://localhost:8000/ws?user_id=${userId}&init_data=${encodeURIComponent(initDataRaw)}`;
      
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt to reconnect unless it was a manual disconnect
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`Reconnecting in ${delay}ms... (attempt ${reconnectAttempts.current + 1})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('WebSocket connection error');
      };

      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('WebSocket message received:', message);
          
          setLastMessage(message);
          handleWebSocketMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

    } catch (error: any) {
      console.error('Error creating WebSocket connection:', error);
      setError(error.message || 'Failed to connect to WebSocket');
    }
  };

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.event) {
      case 'new_ai_draft':
        console.log('New AI draft received:', message.data);
        // Refresh drafts to get the new one
        if (initDataRaw) {
          fetchDrafts(initDataRaw);
        }
        break;

      case 'draft_update':
        console.log('Draft updated:', message.data);
        // Update current draft if it matches
        if (message.data && message.data.id) {
          setCurrentDraft(message.data);
        }
        // Refresh drafts to ensure consistency
        if (initDataRaw) {
          fetchDrafts(initDataRaw);
        }
        break;

      case 'draft_posted':
        console.log('Draft posted successfully:', message.data);
        if (initDataRaw) {
          fetchDrafts(initDataRaw);
        }
        break;

      case 'draft_failed':
        console.log('Draft posting failed:', message.data);
        if (initDataRaw) {
          fetchDrafts(initDataRaw);
        }
        break;

      case 'ai_generation_started':
        console.log('AI generation started for user:', message.user_id);
        break;

      case 'ai_generation_completed':
        console.log('AI generation completed:', message.data);
        if (initDataRaw) {
          fetchDrafts(initDataRaw);
        }
        break;

      case 'system_notification':
        console.log('System notification:', message.data);
        break;

      default:
        console.log('Unknown WebSocket event:', message.event);
    }
  };

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (ws.current) {
      ws.current.close(1000, 'Manual disconnect');
      ws.current = null;
    }

    setIsConnected(false);
    setError(null);
  };

  const sendMessage = (message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  };

  // Connect when userId and initDataRaw are available
  useEffect(() => {
    if (userId && initDataRaw) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [userId, initDataRaw]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    connect,
    disconnect,
  };
}; 