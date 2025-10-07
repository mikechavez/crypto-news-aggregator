import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { narrativesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, formatNumber } from '../lib/formatters';

export function Narratives() {
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set());
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['narratives'],
    queryFn: () => narrativesAPI.getNarratives(),
    refetchInterval: 60000, // 60 seconds
  });

  const narratives = data || [];

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Emerging Narratives</h1>
        <p className="mt-2 text-gray-600">
          Clustered stories and trending topics in the crypto space
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 mt-2">
            Last updated: {formatRelativeTime(new Date(dataUpdatedAt).toISOString())}
          </p>
        )}
      </div>

      <div className="space-y-6">
        {narratives.map((narrative, index) => {
          // Handle both old and new field names for backward compatibility
          const displayTitle = narrative.title || narrative.theme;
          const displaySummary = narrative.summary || narrative.story;
          const displayUpdated = narrative.last_updated || narrative.updated_at;
          
          return (
          <Card key={`${narrative.theme}-${index}`}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle>{displayTitle}</CardTitle>
                <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">
                  {formatNumber(narrative.article_count)} articles
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {displaySummary && (
                <p className="text-gray-700 mb-4">{displaySummary}</p>
              )}
              
              <div className="flex flex-wrap gap-2 mb-4">
                {narrative.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm"
                  >
                    {entity}
                  </span>
                ))}
              </div>

              {/* Articles section */}
              {narrative.articles && narrative.articles.length > 0 && (
                <div className="mb-4 pt-4 border-t border-gray-200">
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
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                  >
                    {expandedArticles.has(index) ? '▼' : '▶'} 📰 View {narrative.articles.length} articles
                  </button>
                  
                  {expandedArticles.has(index) && (
                    <div className="mt-3 space-y-2">
                      {narrative.articles.map((article, articleIdx) => (
                        <div key={articleIdx} className="text-sm bg-gray-50 p-3 rounded">
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 hover:underline font-medium block mb-1"
                          >
                            {article.title}
                          </a>
                          <div className="flex items-center gap-2 text-gray-500 text-xs">
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

              <div className="flex items-center justify-end text-sm text-gray-500 pt-4 border-t border-gray-200">
                <span>Updated {formatRelativeTime(displayUpdated || '')}</span>
              </div>
            </CardContent>
          </Card>
          );
        })}
      </div>

      {narratives.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No narratives detected yet</p>
        </div>
      )}
    </div>
  );
}
