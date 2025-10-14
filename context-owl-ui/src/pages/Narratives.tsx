import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, TrendingUp, Flame, Zap, Star, Wind } from 'lucide-react';
import { narrativesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, formatNumber } from '../lib/formatters';
import { cn } from '../lib/cn';

// Lifecycle configuration with icons, colors, and glow effects
const lifecycleConfig = {
  emerging: { icon: Sparkles, color: 'blue-400', glow: 'shadow-glow-blue', label: 'Emerging' },
  rising: { icon: TrendingUp, color: 'green-400', glow: 'shadow-glow-green', label: 'Rising' },
  hot: { icon: Flame, color: 'orange-400', glow: 'shadow-glow-orange', label: 'Hot' },
  heating: { icon: Zap, color: 'red-400', glow: 'shadow-glow-red', label: 'Heating' },
  mature: { icon: Star, color: 'purple-400', glow: 'shadow-glow-purple', label: 'Mature' },
  cooling: { icon: Wind, color: 'gray-400', glow: '', label: 'Cooling' },
} as const;

/**
 * Safely parse narrative date values to ISO string format
 * Handles null, undefined, invalid dates, and various date formats
 */
const parseNarrativeDate = (dateValue: any): string => {
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
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Emerging Narratives</h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Clustered stories and trending topics in the crypto space
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Last updated: {formatRelativeTime(parseNarrativeDate(dataUpdatedAt))}
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
              <div className="flex items-start justify-between gap-4">
                <CardTitle>{displayTitle}</CardTitle>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Lifecycle badge */}
                  {narrative.lifecycle_stage && lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig] && (
                    <span className={cn(
                      'flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full',
                      `text-${lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].color}`,
                      `bg-${lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].color}/10`,
                      `dark:bg-${lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].color}/20`,
                      lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].glow
                    )}>
                      {(() => {
                        const Icon = lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].icon;
                        return <Icon className="w-4 h-4" />;
                      })()}
                      {lifecycleConfig[narrative.lifecycle_stage as keyof typeof lifecycleConfig].label}
                    </span>
                  )}
                  {/* Article count badge */}
                  <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-full">
                    {formatNumber(narrative.article_count)} articles
                  </span>
                  {/* Mention velocity badge */}
                  {narrative.mention_velocity && narrative.mention_velocity > 0 && (
                    <span className="text-sm font-semibold text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-3 py-1 rounded-full">
                      +{formatNumber(narrative.mention_velocity)} articles/day
                    </span>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {displaySummary && (
                <p className="text-gray-700 dark:text-gray-300 mb-4">{displaySummary}</p>
              )}
              
              <div className="flex flex-wrap gap-2 mb-4">
                {narrative.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 px-2 py-1 rounded text-sm"
                  >
                    {entity}
                  </span>
                ))}
              </div>

              {/* Articles section */}
              {narrative.articles && narrative.articles.length > 0 && (
                <div className="mb-4 pt-4 border-t border-gray-200 dark:border-dark-border">
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
                    className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium flex items-center gap-1"
                  >
                    {expandedArticles.has(index) ? '▼' : '▶'} 📰 View {narrative.articles.length} articles
                  </button>
                  
                  {expandedArticles.has(index) && (
                    <div className="mt-3 space-y-2">
                      {narrative.articles.map((article, articleIdx) => (
                        <div key={articleIdx} className="text-sm bg-gray-50 dark:bg-dark-hover p-3 rounded">
                          <a
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline font-medium block mb-1"
                          >
                            {article.title}
                          </a>
                          <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-xs">
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

              <div className="flex items-center justify-end text-sm text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-dark-border">
                <span>Updated {formatRelativeTime(parseNarrativeDate(displayUpdated))}</span>
              </div>
            </CardContent>
          </Card>
          );
        })}
      </div>

      {narratives.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">No narratives detected yet</p>
        </div>
      )}
    </div>
  );
}
