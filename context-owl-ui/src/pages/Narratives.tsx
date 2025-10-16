import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, TrendingUp, Flame, Zap, Star, Wind, LayoutGrid, Activity, Archive } from 'lucide-react';
import { narrativesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { TimelineView } from '../components/TimelineView';
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
  const [viewMode, setViewMode] = useState<'cards' | 'pulse' | 'archive'>('cards');
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['narratives', viewMode],
    queryFn: () => viewMode === 'archive' ? narrativesAPI.getResurrectedNarratives(20, 7) : narrativesAPI.getNarratives(),
    refetchInterval: 60000, // 60 seconds
  });

  const narratives = data || [];

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          {viewMode === 'archive' ? 'Archived Narratives' : 'Emerging Narratives'}
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          {viewMode === 'archive' 
            ? 'Dormant narratives that have been reactivated in the past 7 days'
            : 'Clustered stories and trending topics in the crypto space'
          }
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Last updated: {formatRelativeTime(parseNarrativeDate(dataUpdatedAt))}
          </p>
        )}
      </div>

      {/* View mode toggle */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setViewMode('cards')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
            viewMode === 'cards'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-dark-hover'
          )}
        >
          <LayoutGrid className="w-4 h-4" />
          Cards
        </button>
        <button
          onClick={() => setViewMode('pulse')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
            viewMode === 'pulse'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-dark-hover'
          )}
        >
          <Activity className="w-4 h-4" />
          Pulse
        </button>
        <button
          onClick={() => setViewMode('archive')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
            viewMode === 'archive'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-dark-hover'
          )}
        >
          <Archive className="w-4 h-4" />
          Archive
        </button>
      </div>

      {viewMode === 'pulse' ? (
        <>
          <TimelineView narratives={narratives || []} />
        </>
      ) : (
        <>
      {/* Resurrection Summary Card - only shown in archive view */}
      {viewMode === 'archive' && narratives.length > 0 && (
        <Card className="mb-6 bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 border-2 border-amber-300 dark:border-amber-700">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500 dark:bg-amber-600 rounded-lg">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <CardTitle className="text-amber-900 dark:text-amber-100">
                Resurrection Summary
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Total count */}
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-amber-900 dark:text-amber-100">
                  {narratives.length}
                </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {narratives.length === 1 ? 'narrative has' : 'narratives have'} been resurrected in the past 7 days
                </span>
              </div>

              {/* Top Resurrections */}
              {narratives.length > 0 && (
                <div className="pt-4 border-t border-amber-200 dark:border-amber-800">
                  <h3 className="text-lg font-semibold text-amber-900 dark:text-amber-100 mb-3">
                    ⚡ Top Resurrections
                  </h3>
                  <div className="space-y-3">
                    {narratives
                      .filter(n => n.reawakening_count && n.reawakening_count > 0)
                      .sort((a, b) => (b.reawakening_count || 0) - (a.reawakening_count || 0))
                      .slice(0, 3)
                      .map((narrative, idx) => {
                        const displayTitle = narrative.title || narrative.theme;
                        return (
                          <div 
                            key={idx}
                            className="flex items-start justify-between gap-4 p-3 bg-white/50 dark:bg-gray-900/30 rounded-lg"
                          >
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-lg font-bold text-amber-700 dark:text-amber-400">
                                  #{idx + 1}
                                </span>
                                <h4 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                                  {displayTitle}
                                </h4>
                              </div>
                              <div className="flex flex-wrap gap-3 text-sm">
                                <span className="flex items-center gap-1 text-amber-700 dark:text-amber-400 font-medium">
                                  <Zap className="w-3.5 h-3.5" />
                                  {narrative.reawakening_count}x reawakened
                                </span>
                                {narrative.resurrection_velocity && narrative.resurrection_velocity > 0 && (
                                  <span className="text-green-700 dark:text-green-400 font-medium">
                                    +{formatNumber(narrative.resurrection_velocity)} resurrections/day
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {narratives.map((narrative, index) => {
          // Handle both old and new field names for backward compatibility
          const displayTitle = narrative.title || narrative.theme;
          const displaySummary = narrative.summary || narrative.story;
          const displayUpdated = narrative.last_updated || narrative.updated_at;
          
          return (
          <Card key={`${narrative.theme}-${index}`} className={cn(
            viewMode === 'archive' && 'border-2 border-purple-300 dark:border-purple-700 bg-purple-50/30 dark:bg-purple-900/10'
          )}>
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2 flex-wrap">
                  {viewMode === 'archive' && (
                    <Archive className="w-5 h-5 text-purple-600 dark:text-purple-400 flex-shrink-0" />
                  )}
                  <CardTitle>{displayTitle}</CardTitle>
                  {/* Reawakened badge */}
                  {viewMode === 'archive' && narrative.reawakening_count && narrative.reawakening_count > 0 && (
                    <span className="flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-300">
                      <Zap className="w-4 h-4" />
                      Reawakened{narrative.reawakening_count > 1 ? ` ${narrative.reawakening_count}x` : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Lifecycle badge */}
                  {(() => {
                    const lifecycleValue = narrative.lifecycle_state || narrative.lifecycle;
                    const config = lifecycleValue && lifecycleConfig[lifecycleValue as keyof typeof lifecycleConfig];
                    if (!config) return null;
                    
                    const Icon = config.icon;
                    return (
                      <span className={cn(
                        'flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full',
                        `text-${config.color}`,
                        `bg-${config.color}/10`,
                        `dark:bg-${config.color}/20`,
                        config.glow
                      )}>
                        <Icon className="w-4 h-4" />
                        {config.label}
                      </span>
                    );
                  })()}
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

              <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-dark-border">
                {viewMode === 'archive' && narrative.reawakened_from && (
                  <span className="text-amber-700 dark:text-amber-400 font-medium">
                    Dormant since {formatRelativeTime(parseNarrativeDate(narrative.reawakened_from))}
                  </span>
                )}
                <span className={cn(viewMode === 'archive' && narrative.reawakened_from ? '' : 'ml-auto')}>
                  Updated {formatRelativeTime(parseNarrativeDate(displayUpdated))}
                </span>
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
        </>
      )}
    </div>
  );
}
