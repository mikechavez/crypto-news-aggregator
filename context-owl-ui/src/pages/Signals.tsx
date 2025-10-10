import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { signalsAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, formatSentiment, getSentimentColor, formatEntityType, getEntityTypeColor, formatTheme, getThemeColor } from '../lib/formatters';

/**
 * Safely parse date values to ISO string format
 * Handles null, undefined, invalid dates, and various date formats
 */
const parseDateSafe = (dateValue: any): string => {
  // Handle null, undefined, or empty values
  if (!dateValue) return new Date().toISOString();
  
  // If it's already a Date object, convert to ISO string
  if (dateValue instanceof Date) {
    return isNaN(dateValue.getTime()) ? new Date().toISOString() : dateValue.toISOString();
  }
  
  // If it's a string, validate it can be parsed
  if (typeof dateValue === 'string') {
    // Return as-is if it's already a valid date string
    const date = new Date(dateValue);
    if (!isNaN(date.getTime())) {
      return dateValue;
    }
  }
  
  // Try to convert any other type to a date
  try {
    const date = new Date(dateValue);
    return isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
  } catch {
    return new Date().toISOString();
  }
};

/**
 * Get velocity indicator based on velocity value
 * Returns emoji, label, and color classes for the badge
 * 
 * Velocity is a percentage (e.g., 1379 = 1379% growth = 13.79x increase)
 * Thresholds:
 * - Surging: >= 500 (500%+ growth, 5x or more - truly explosive)
 * - Rising: >= 200 (200%+ growth, 2x-5x - strong growth)
 * - Growing: >= 50 (50%+ growth, 1.5x-2x - moderate growth)
 * - Active: >= 0 (0-50% growth - steady)
 * - Declining: < 0 (negative growth - losing momentum)
 */
const getVelocityIndicator = (velocity: number): { emoji: string; label: string; colorClass: string } => {
  if (velocity >= 500) {
    return { emoji: '🔥', label: 'Surging', colorClass: 'bg-red-100 text-red-700' };
  } else if (velocity >= 200) {
    return { emoji: '↑', label: 'Rising', colorClass: 'bg-green-100 text-green-700' };
  } else if (velocity >= 50) {
    return { emoji: '→', label: 'Growing', colorClass: 'bg-blue-100 text-blue-700' };
  } else if (velocity >= 0) {
    return { emoji: '', label: 'Active', colorClass: 'bg-gray-100 text-gray-700' };
  } else {
    return { emoji: '↓', label: 'Declining', colorClass: 'bg-orange-100 text-orange-700' };
  }
};

type Timeframe = '24h' | '7d' | '30d';

interface TabConfig {
  id: Timeframe;
  label: string;
  emoji: string;
  description: string;
}

const TABS: TabConfig[] = [
  { id: '24h', label: 'Hot', emoji: '🔥', description: 'Breaking news and sudden spikes' },
  { id: '7d', label: 'Trending', emoji: '📈', description: 'Gaining momentum this week' },
  { id: '30d', label: 'Top', emoji: '⭐', description: 'Major ongoing narratives' },
];

export function Signals() {
  const navigate = useNavigate();
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set());
  const [selectedTimeframe, setSelectedTimeframe] = useState<Timeframe>('7d');
  
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['signals', selectedTimeframe],
    queryFn: () => signalsAPI.getSignals({ limit: 10, timeframe: selectedTimeframe }),
    refetchInterval: 30000, // 30 seconds
    staleTime: 0, // Always consider data stale
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  // Debug: Log the first signal to see if recent_articles is present
  if (data?.signals && data.signals.length > 0) {
    console.log('First signal data:', data.signals[0]);
    console.log('Has recent_articles?', 'recent_articles' in data.signals[0]);
    console.log('Recent articles count:', data.signals[0].recent_articles?.length);
  }

  const currentTab = TABS.find(tab => tab.id === selectedTimeframe) || TABS[1];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Market Signals</h1>
        <p className="mt-2 text-gray-600">
          Real-time detection of unusual market activity and emerging trends
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 mt-2">
            Last updated: {formatRelativeTime(parseDateSafe(dataUpdatedAt))}
          </p>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="mb-6">
        <div className="flex gap-2 border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedTimeframe(tab.id)}
              className={`px-4 py-3 font-medium text-sm transition-colors relative ${
                selectedTimeframe === tab.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <span className="mr-2">{tab.emoji}</span>
              {tab.label} ({tab.id})
            </button>
          ))}
        </div>
        <p className="mt-3 text-sm text-gray-600">
          {currentTab.description}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {data?.signals.map((signal, index) => {
          const ticker = signal.entity.match(/\$[A-Z]+/)?.[0];
          const entityName = signal.entity.replace(/\$[A-Z]+/g, '').trim();
          
          const velocityIndicator = getVelocityIndicator(signal.velocity);
          
          return (
          <Card key={`${signal.entity}-${index}`}>
            <CardHeader>
              <CardTitle className="text-lg">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-blue-600 font-bold">#{index + 1}</span>
                  {/* TODO: Add Link to entity detail when endpoints ready */}
                  <span>{entityName}</span>
                  {ticker && <span className="text-gray-500">{ticker}</span>}
                  <span className={`text-xs font-medium px-2 py-1 rounded-full ${velocityIndicator.colorClass}`}>
                    {velocityIndicator.emoji} {velocityIndicator.label}
                  </span>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Type:</span>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEntityTypeColor(signal.entity_type)}`}>
                    {formatEntityType(signal.entity_type)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Sources:</span>
                  <span className="text-gray-700">
                    {signal.source_count} sources
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Sentiment:</span>
                  <span className={getSentimentColor(signal.sentiment)}>
                    {formatSentiment(signal.sentiment)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Last Updated:</span>
                  <span className="text-gray-700">
                    {formatRelativeTime(parseDateSafe(signal.last_updated))}
                  </span>
                </div>
                
                {/* Narrative context section */}
                <div className="mt-3 pt-3 border-t border-gray-200">
                  {signal.is_emerging ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-yellow-700 bg-yellow-100 px-2 py-1 rounded-full">
                        🆕 Emerging
                      </span>
                      <span className="text-xs text-gray-500">Not yet part of any narrative</span>
                    </div>
                  ) : signal.narratives && signal.narratives.length > 0 ? (
                    <div>
                      <span className="text-xs text-gray-500 block mb-1">Part of:</span>
                      <div className="flex flex-wrap gap-1">
                        {signal.narratives.map((narrative) => (
                          <button
                            key={narrative.id}
                            onClick={() => navigate('/narratives')}
                            className={`text-xs font-medium px-2 py-1 rounded-full transition-colors ${getThemeColor(narrative.theme)}`}
                            title={narrative.title}
                          >
                            {formatTheme(narrative.theme)}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
                
                {/* Recent articles section */}
                {signal.recent_articles && signal.recent_articles.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <button
                      onClick={() => {
                        const newExpanded = new Set(expandedArticles);
                        if (newExpanded.has(index)) {
                          newExpanded.delete(index);
                        } else {
                          newExpanded.add(index);
                        }
                        setExpandedArticles(newExpanded);
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                    >
                      {expandedArticles.has(index) ? '▼' : '▶'} Recent mentions ({signal.recent_articles.length})
                    </button>
                    
                    {expandedArticles.has(index) && (
                      <div className="mt-2 space-y-2">
                        {signal.recent_articles.map((article, articleIdx) => (
                          <div key={articleIdx} className="text-xs bg-gray-50 p-2 rounded">
                            <a
                              href={article.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 hover:text-blue-800 hover:underline font-medium block mb-1"
                            >
                              {article.title}
                            </a>
                            <div className="flex items-center gap-2 text-gray-500">
                              <span className="capitalize">{article.source}</span>
                              <span>•</span>
                              <span>{formatRelativeTime(article.published_at)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
          );
        })}
      </div>

      {data?.signals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No signals detected yet</p>
        </div>
      )}
    </div>
  );
}
