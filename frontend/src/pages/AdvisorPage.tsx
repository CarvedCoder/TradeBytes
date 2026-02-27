/**
 * AI Advisor Page - RAG-powered financial strategy assistant with conversation history.
 */

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { Bot, Send, Loader2, Lightbulb } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: { title: string; url?: string }[];
  suggestedActions?: { type: string; ticker: string; reasoning: string }[];
  timestamp: string;
}

const SUGGESTED_PROMPTS = [
  'Analyze my portfolio risk exposure',
  'What stocks should I consider based on current sentiment?',
  'Explain my recent trading performance',
  'Create a diversification strategy for my holdings',
  'What are the key market trends this week?',
];

export default function AdvisorPage() {
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const queryMutation = useMutation({
    mutationFn: (query: string) =>
      api.post('/ai-advisor/query', { query, conversation_id: conversationId }).then((r) => r.data),
    onSuccess: (data) => {
      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          sources: data.sources,
          suggestedActions: data.suggested_actions,
          timestamp: new Date().toISOString(),
        },
      ]);
    },
  });

  const { data: conversations } = useQuery({
    queryKey: ['advisor-conversations'],
    queryFn: () => api.get('/ai-advisor/conversations').then((r) => r.data),
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (text?: string) => {
    const query = text ?? input;
    if (!query.trim()) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query, timestamp: new Date().toISOString() },
    ]);
    setInput('');
    queryMutation.mutate(query);
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* Conversation History Sidebar */}
      <div className="hidden w-64 flex-col rounded-xl border border-surface-700 bg-surface-900 p-3 lg:flex">
        <div className="mb-3 flex items-center gap-2 px-2">
          <Bot className="h-4 w-4 text-primary-400" />
          <span className="text-sm font-semibold text-white">Conversations</span>
        </div>
        <button
          onClick={() => { setConversationId(null); setMessages([]); }}
          className="btn-primary mb-3 w-full text-sm"
        >
          New Conversation
        </button>
        <div className="flex-1 space-y-1 overflow-auto">
          {(conversations?.conversations ?? []).map((conv: any) => (
            <button
              key={conv.id}
              onClick={() => setConversationId(conv.id)}
              className={cn(
                'w-full rounded-lg px-3 py-2 text-left text-sm transition-colors',
                conversationId === conv.id
                  ? 'bg-primary-600/20 text-primary-300'
                  : 'text-surface-200 hover:bg-surface-800',
              )}
            >
              <p className="truncate">{conv.title ?? 'Conversation'}</p>
              <p className="text-xs text-surface-200">{conv.message_count} messages</p>
            </button>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex flex-1 flex-col rounded-xl border border-surface-700 bg-surface-900">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-surface-700 px-4 py-3">
          <Bot className="h-5 w-5 text-primary-400" />
          <span className="font-semibold text-white">AI Financial Advisor</span>
          <span className="text-xs text-surface-200">Powered by RAG + your portfolio data</span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-auto p-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center">
              <Bot className="mb-4 h-12 w-12 text-primary-500/50" />
              <h2 className="mb-2 text-lg font-semibold text-white">Ask me anything about finance</h2>
              <p className="mb-6 text-sm text-surface-200">
                I have access to your portfolio, trade history, market news, and AI predictions.
              </p>
              <div className="grid max-w-md grid-cols-1 gap-2">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSend(prompt)}
                    className="flex items-center gap-2 rounded-lg border border-surface-700 bg-surface-800 px-4 py-2.5 text-left text-sm text-surface-200 transition-colors hover:border-primary-500/50 hover:text-white"
                  >
                    <Lightbulb className="h-4 w-4 shrink-0 text-warning" />
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={cn('flex gap-3', msg.role === 'user' && 'justify-end')}>
                {msg.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600">
                    <Bot className="h-4 w-4" />
                  </div>
                )}
                <div className={cn(
                  'max-w-2xl rounded-lg px-4 py-3',
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white'
                    : 'bg-surface-800 text-white',
                )}>
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 border-t border-surface-700 pt-2">
                      <p className="mb-1 text-xs font-medium text-surface-200">Sources:</p>
                      {msg.sources.map((s, j) => (
                        <a
                          key={j}
                          href={s.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="block text-xs text-primary-400 hover:underline"
                        >
                          {s.title}
                        </a>
                      ))}
                    </div>
                  )}

                  {/* Suggested Actions */}
                  {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-surface-700 pt-2">
                      <p className="text-xs font-medium text-surface-200">Suggested Actions:</p>
                      {msg.suggestedActions.map((action, j) => (
                        <div key={j} className="rounded border border-surface-700 bg-surface-900 p-2">
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              'badge',
                              action.type === 'buy' ? 'badge-success' : 'badge-danger'
                            )}>
                              {action.type.toUpperCase()}
                            </span>
                            <span className="text-sm font-medium">{action.ticker}</span>
                          </div>
                          <p className="mt-1 text-xs text-surface-200">{action.reasoning}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {queryMutation.isPending && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-600">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-lg bg-surface-800 px-4 py-3">
                  <Loader2 className="h-5 w-5 animate-spin text-primary-400" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-surface-700 p-3">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
              placeholder="Ask about your portfolio, market trends, or trading strategies..."
              className="input-field"
              disabled={queryMutation.isPending}
            />
            <button
              onClick={() => handleSend()}
              disabled={queryMutation.isPending || !input.trim()}
              className="btn-primary !px-3"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
