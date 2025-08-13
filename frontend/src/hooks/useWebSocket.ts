import { useEffect, useRef, useState } from 'react';
import { Centrifuge } from 'centrifuge';

interface WebSocketMessage {
  event: string;
  data: any;
  user_id?: string;
}

interface UseWebSocketProps {
  userId?: string;
  initDataRaw?: string | null;
}

async function fetchWsToken(): Promise<string | undefined> {
  try {
    const base = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const res = await fetch(`${base}/auth/ws-token`, { credentials: 'include' });
    const json = await res.json();
    if (json?.success && json?.data?.token) return json.data.token;
  } catch (e) {
    console.error('Failed to get WS token', e);
  }
}

export const useWebSocket = ({ userId, initDataRaw }: UseWebSocketProps) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const centrifugeRef = useRef<Centrifuge | null>(null);
  const subRef = useRef<ReturnType<Centrifuge['newSubscription']> | null>(null);

  const connect = async () => {
    try {
      if (!userId) return;
      // Prevent duplicate connections in React Strict Mode
      if (centrifugeRef.current) return;
      const wsUrl = process.env.NEXT_PUBLIC_CENTRIFUGO_WS_URL || 'ws://localhost:9000/connection/websocket';
      const token = await fetchWsToken();
      console.log('Connecting to Centrifugo', { wsUrl, hasToken: !!token, userId });

      const centrifuge = new Centrifuge(
        wsUrl,
        token
          ? {
              token,
              // Auto-refresh token when expired (code 12)
              getToken: async () => {
                try {
                  const t = await fetchWsToken();
                  if (!t) throw new Error('no token');
                  return t;
                } catch (e) {
                  console.error('Failed to refresh WS token', e);
                  return '' as unknown as string;
                }
              },
            }
          : {}
      );
      centrifugeRef.current = centrifuge;

      centrifuge.on('connected', () => {
        console.log('Centrifugo connected');
        setIsConnected(true);
        setError(null);
      });
      centrifuge.on('disconnected', () => {
        console.log('Centrifugo disconnected');
        setIsConnected(false);
      });
      centrifuge.on('error', async (ctx: any) => {
        setError(ctx?.message || 'Centrifugo error');
        console.error('Centrifugo error', ctx);
        const code = ctx?.code;
        if (code === 109 || code === 112) {
          try {
            const newToken = await fetchWsToken();
            if (newToken && centrifugeRef.current) {
              centrifugeRef.current.setToken(newToken);
              centrifugeRef.current.disconnect();
              centrifugeRef.current.connect();
            } else {
              disconnect();
              setTimeout(connect, 500);
            }
          } catch {
            disconnect();
            setTimeout(connect, 1000);
          }
        }
      });

      centrifuge.connect();

      const channel = `user:${userId}`;
      // Reuse existing subscription if present
      const sub = subRef.current ?? centrifuge.newSubscription(channel);
      subRef.current = sub;

      sub.on('publication', (ctx) => {
        console.log('Centrifugo publication', ctx);
        const msg = (ctx as any).data as WebSocketMessage;
        setLastMessage(msg);
      });

      sub.on('subscribed', () => {
        console.log('Subscribed to', channel);
      });
      sub.on('error', (e) => {
        console.error('Subscription error', e);
      });

      if ((sub as any)._state !== 2 /* subscribed */) {
        sub.subscribe();
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to connect to Centrifugo');
      console.error('Failed to connect to Centrifugo', e);
    }
  };

  const disconnect = () => {
    try {
      subRef.current?.unsubscribe();
      subRef.current = null;
      centrifugeRef.current?.disconnect();
      centrifugeRef.current = null;
    } catch {}
    setIsConnected(false);
    setError(null);
  };

  useEffect(() => {
    console.log('useWebSocket mount', { userId });
    if (userId) connect();
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  return {
    isConnected,
    lastMessage,
    error,
    connect,
    disconnect,
  };
}; 