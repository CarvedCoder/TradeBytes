/**
 * Community Page - Real-time chat channels via WebSocket + REST history.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { createCommunityWS, WebSocketClient } from '@/lib/websocket';
import api from '@/lib/api';
import { formatTimeAgo, cn } from '@/lib/utils';
import { Users, Send, Hash, Circle, Loader2 } from 'lucide-react';

interface ChatMessage {
  id?: string;
  user_id: string;
  display_name?: string;
  username?: string;
  avatar_url?: string | null;
  content: string;
  timestamp: string;
}

const CHANNELS = ['general', 'trading', 'technical-analysis', 'news', 'beginners'];

export default function CommunityPage() {
  const [activeChannel, setActiveChannel] = useState('general');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [onlineUsers, setOnlineUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocketClient | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const user = useAuthStore((s) => s.user);

  // Load persisted message history from REST API
  const loadHistory = useCallback(async (channel: string) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/community/messages/${channel}?limit=50`);
      const mapped: ChatMessage[] = (data ?? []).map((m: any) => ({
        id: m.id,
        user_id: m.user_id,
        display_name: m.display_name,
        username: m.username,
        avatar_url: m.avatar_url,
        content: m.content,
        timestamp: m.created_at,
      }));
      setMessages(mapped);
    } catch {
      // On error just start with empty messages
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Load history first, then connect WS for live messages
    loadHistory(activeChannel);

    const ws = createCommunityWS(activeChannel, (msg) => {
      switch (msg.type) {
        case 'chat_message':
          setMessages((prev) => [
            ...prev,
            {
              id: msg.id as string,
              user_id: msg.user_id as string,
              display_name: msg.display_name as string,
              username: msg.username as string,
              avatar_url: msg.avatar_url as string | null,
              content: msg.content as string,
              timestamp: msg.timestamp as string,
            },
          ]);
          break;
        case 'channel_state':
          setOnlineUsers((msg as any).online_users ?? []);
          break;
        case 'user_joined':
          setOnlineUsers((prev) => [...new Set([...prev, msg.user_id as string])]);
          break;
        case 'user_left':
          setOnlineUsers((prev) => prev.filter((id) => id !== msg.user_id));
          break;
      }
    });
    ws.connect();
    wsRef.current = ws;

    return () => ws.disconnect();
  }, [activeChannel, loadHistory]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = () => {
    if (!inputValue.trim()) return;
    wsRef.current?.send({ type: 'message', content: inputValue });
    setInputValue('');
  };

  const displayName = (msg: ChatMessage) =>
    msg.display_name || msg.username || msg.user_id?.slice(0, 8) || '?';

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* Channel List */}
      <div className="w-56 rounded-xl border border-surface-700 bg-surface-900 p-3">
        <div className="mb-3 flex items-center gap-2 px-2">
          <Users className="h-4 w-4 text-surface-200" />
          <span className="text-sm font-semibold text-white">Channels</span>
        </div>
        <nav className="space-y-1">
          {CHANNELS.map((ch) => (
            <button
              key={ch}
              onClick={() => setActiveChannel(ch)}
              className={cn(
                'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                activeChannel === ch
                  ? 'bg-primary-600/20 text-primary-300'
                  : 'text-surface-200 hover:bg-surface-800',
              )}
            >
              <Hash className="h-3.5 w-3.5" />
              {ch}
            </button>
          ))}
        </nav>

        {/* Online Users */}
        <div className="mt-6 border-t border-surface-700 pt-3">
          <p className="mb-2 px-2 text-xs font-medium text-surface-200">
            Online — {onlineUsers.length}
          </p>
          <div className="space-y-1">
            {onlineUsers.slice(0, 10).map((uid) => (
              <div key={uid} className="flex items-center gap-2 px-2 text-xs text-surface-200">
                <Circle className="h-2 w-2 fill-success text-success" />
                <span className="truncate">{uid.slice(0, 8)}...</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex flex-1 flex-col rounded-xl border border-surface-700 bg-surface-900">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-surface-700 px-4 py-3">
          <Hash className="h-4 w-4 text-surface-200" />
          <span className="font-semibold text-white">{activeChannel}</span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex h-full items-center justify-center text-surface-200">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              <span>Loading messages…</span>
            </div>
          ) : (
          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={msg.id ?? i} className={cn('flex gap-3', msg.user_id === user?.id && 'justify-end')}>
                {msg.user_id !== user?.id && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600 text-xs font-bold">
                    {displayName(msg).charAt(0).toUpperCase()}
                  </div>
                )}
                <div className={cn(
                  'max-w-md rounded-lg px-3 py-2',
                  msg.user_id === user?.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-surface-800 text-white',
                )}>
                  {msg.user_id !== user?.id && (
                    <p className="mb-0.5 text-xs font-medium text-primary-300">
                      {displayName(msg)}
                    </p>
                  )}
                  <p className="text-sm">{msg.content}</p>
                  <p className="mt-1 text-right text-[10px] opacity-50">
                    {formatTimeAgo(msg.timestamp)}
                  </p>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
          )}

          {!loading && messages.length === 0 && (
            <div className="flex h-full items-center justify-center text-surface-200">
              <p>No messages yet. Say hello! 👋</p>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-surface-700 p-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder={`Message #${activeChannel}`}
              className="input-field"
            />
            <button onClick={sendMessage} className="btn-primary !px-3">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
