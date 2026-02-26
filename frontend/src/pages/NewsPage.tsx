/**
 * News Intelligence Page - Financial news feed with sentiment analysis overlay.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatTimeAgo, cn } from '@/lib/utils';
import { Newspaper, TrendingUp, TrendingDown, Minus, Search, ExternalLink } from 'lucide-react';

export default function NewsPage() {
  const [searchTicker, setSearchTicker] = useState('');

  const { data: newsFeed } = useQuery({
    queryKey: ['news-feed'],
    queryFn: () => api.get('/news/feed?limit=20').then((r) => r.data),
  });

  const { data: tickerSentiment } = useQuery({
    queryKey: ['ticker-sentiment', searchTicker],
    queryFn: () => api.get(`/news/sentiment/${searchTicker}`).then((r) => r.data),
    enabled: !!searchTicker,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">News Intelligence</h1>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-surface-200" />
            <input
              type="text"
              placeholder="Search ticker (e.g. AAPL)"
              value={searchTicker}
              onChange={(e) => setSearchTicker(e.target.value.toUpperCase())}
              className="input-field !pl-10"
            />
          </div>
        </div>
      </div>

      {/* Ticker Sentiment */}
      {tickerSentiment && (
        <div className="card border-primary-500/30">
          <h2 className="mb-3 text-lg font-semibold text-white">
            {searchTicker} Sentiment Analysis
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-success">{(tickerSentiment.positive * 100).toFixed(0)}%</p>
              <p className="text-xs text-surface-200">Bullish</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-surface-200">{(tickerSentiment.neutral * 100).toFixed(0)}%</p>
              <p className="text-xs text-surface-200">Neutral</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-danger">{(tickerSentiment.negative * 100).toFixed(0)}%</p>
              <p className="text-xs text-surface-200">Bearish</p>
            </div>
          </div>
          {/* Sentiment bar */}
          <div className="mt-3 flex h-2 overflow-hidden rounded-full">
            <div className="bg-success" style={{ width: `${tickerSentiment.positive * 100}%` }} />
            <div className="bg-surface-200" style={{ width: `${tickerSentiment.neutral * 100}%` }} />
            <div className="bg-danger" style={{ width: `${tickerSentiment.negative * 100}%` }} />
          </div>
        </div>
      )}

      {/* News Feed */}
      <div className="space-y-3">
        {(newsFeed?.articles ?? []).map((article: any, i: number) => (
          <article key={i} className="card-hover flex gap-4">
            {article.image_url && (
              <img
                src={article.image_url}
                alt=""
                className="h-24 w-32 rounded-lg object-cover"
              />
            )}
            <div className="flex-1">
              <div className="mb-1 flex items-center gap-2">
                <SentimentIndicator score={article.sentiment_score} />
                <span className="text-xs text-surface-200">{article.source}</span>
                <span className="text-xs text-surface-200">•</span>
                <span className="text-xs text-surface-200">
                  {formatTimeAgo(article.published_at)}
                </span>
              </div>
              <h3 className="text-sm font-medium text-white line-clamp-2">{article.title}</h3>
              <p className="mt-1 text-xs text-surface-200 line-clamp-2">{article.description}</p>
              <div className="mt-2 flex items-center gap-2">
                {(article.mentioned_tickers ?? []).map((t: string) => (
                  <button
                    key={t}
                    onClick={() => setSearchTicker(t)}
                    className="badge-primary cursor-pointer hover:bg-primary-500/30"
                  >
                    {t}
                  </button>
                ))}
                {article.url && (
                  <a
                    href={article.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto flex items-center gap-1 text-xs text-primary-400 hover:underline"
                  >
                    Read <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          </article>
        ))}
        {!newsFeed?.articles?.length && (
          <div className="card text-center text-surface-200">
            <Newspaper className="mx-auto mb-2 h-8 w-8" />
            <p>No news articles yet. Data will populate after ingestion runs.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function SentimentIndicator({ score }: { score: number }) {
  if (score > 0.2)
    return <TrendingUp className="h-4 w-4 text-success" />;
  if (score < -0.2)
    return <TrendingDown className="h-4 w-4 text-danger" />;
  return <Minus className="h-4 w-4 text-surface-200" />;
}
