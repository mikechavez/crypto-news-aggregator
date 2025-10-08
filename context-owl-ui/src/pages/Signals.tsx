import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { signalsAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, getSignalStrengthColor, formatPercentage, formatSentiment, getSentimentColor, formatEntityType, getEntityTypeColor, formatTheme, getThemeColor } from '../lib/formatters';

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

export function Signals() {
  const navigate = useNavigate();
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set());
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['signals'],
    queryFn: () => signalsAPI.getSignals({ limit: 10 }),
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

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {data?.signals.map((signal, index) => {
          const ticker = signal.entity.match(/\$[A-Z]+/)?.[0];
          const entityName = signal.entity.replace(/\$[A-Z]+/g, '').trim();
          
          return (
          <Card key={`${signal.entity}-${index}`}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-lg">
                  <span className="text-blue-600 font-bold mr-2">#{index + 1}</span>
                  {/* TODO: Add Link to entity detail when endpoints ready */}
                  {entityName}
                  {ticker && <span className="text-gray-500 ml-2">{ticker}</span>}
                </CardTitle>
                <span
                  className={`text-sm font-semibold ${getSignalStrengthColor(signal.signal_score)}`}
                >
                  {formatPercentage(signal.signal_score, 0)}
                </span>
              </div>
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
                  <span className="text-gray-500">Velocity:</span>
                  <span className="text-gray-700">
                    {signal.velocity.toFixed(1)} mentions/hr
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
