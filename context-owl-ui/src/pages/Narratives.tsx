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

/**
 * Format date as "MMM DD" (e.g., "Oct 18")
 * This is the canonical date formatter for timeline components
 */
const formatDate = (dateValue: any): string => {
  try {
    const date = new Date(parseNarrativeDate(dateValue));
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return 'Unknown';
  }
};

/**
 * Format relative time in short format (e.g., "2h ago", "3d ago", "1w ago")
 * This is the canonical relative time formatter for timeline components
 */
const formatShortRelativeTime = (dateValue: any): string => {
  try {
    const date = new Date(parseNarrativeDate(dateValue));
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    // After 24 hours, show date format instead of relative time
    return formatDate(dateValue);
  } catch {
    return 'Unknown';
  }
};

/**
 * Format full timestamp for tooltip display
 */
const formatFullTimestamp = (dateValue: any): string => {
  try {
    const date = new Date(parseNarrativeDate(dateValue));
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  } catch {
    return 'Unknown';
  }
};

/**
 * Timeline Header Component
 * Displays the overall date range with a visual reference line
 */
interface TimelineHeaderProps {
  earliest: Date;
  latest: Date;
}

const TimelineHeader: React.FC<TimelineHeaderProps> = ({ earliest, latest }) => {
  // Calculate evenly spaced tick marks between earliest and latest
  const calculateTickMarks = (start: Date, end: Date, count: number = 5) => {
    const ticks: { date: Date; position: number }[] = [];
    const totalDuration = end.getTime() - start.getTime();
    
    // Generate tick marks at evenly spaced intervals
    for (let i = 0; i < count; i++) {
      const position = (i / (count - 1)) * 100; // Position as percentage
      const timestamp = start.getTime() + (totalDuration * i / (count - 1));
      ticks.push({
        date: new Date(timestamp),
        position: position
      });
    }
    
    return ticks;
  };
  
  const tickMarks = calculateTickMarks(earliest, latest, 5);
  
  return (
    <div className="mb-6 px-4">
      {/* Timeline bar with tick marks */}
      <div className="relative">
        {/* Main timeline bar */}
        <div className="h-0.5 bg-gray-300 dark:bg-gray-600 rounded-full" />
        
        {/* Tick marks */}
        <div className="relative h-6">
          {tickMarks.map((tick, index) => (
            <div
              key={index}
              className="absolute"
              style={{ left: `${tick.position}%`, transform: 'translateX(-50%)' }}
            >
              {/* Vertical tick line */}
              <div className="w-px h-2 bg-gray-400 dark:bg-gray-500 mx-auto" />
              {/* Date label */}
              <div className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap mt-1 text-center">
                {formatDate(tick.date)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/**
 * Timeline Bar Component
 * Displays a visual bar showing when a narrative started and was last updated
 * relative to the global timeline, with optional activity density shading
 */
interface TimelineDataPoint {
  date: string;
  article_count: number;
}

interface TimelineBarProps {
  first_seen: any;
  last_updated: any;
  earliest: Date;
  latest: Date;
  lifecycle_state?: string;
  timeline_data?: TimelineDataPoint[];
  tooltipText?: string;
}

const TimelineBar: React.FC<TimelineBarProps> = ({ 
  first_seen, 
  last_updated, 
  earliest, 
  latest, 
  lifecycle_state,
  timeline_data,
  tooltipText
}) => {
  // DEBUG: Log input values
  console.log('[TimelineBar] Input values:', {
    first_seen,
    last_updated,
    earliest,
    latest,
    lifecycle_state
  });

  // Check for null/undefined dates
  if (!first_seen || !last_updated) {
    console.warn('[TimelineBar] Missing date values - first_seen:', first_seen, 'last_updated:', last_updated);
    // Render placeholder bar for missing dates
    return (
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full opacity-40" title="Missing date data" />
    );
  }

  // Parse dates safely
  const firstSeenDate = new Date(parseNarrativeDate(first_seen));
  const lastUpdatedDate = new Date(parseNarrativeDate(last_updated));
  
  // DEBUG: Log parsed dates
  console.log('[TimelineBar] Parsed dates:', {
    firstSeenDate,
    lastSeenTime: firstSeenDate.getTime(),
    firstSeenIsNaN: isNaN(firstSeenDate.getTime()),
    lastUpdatedDate,
    lastUpdatedTime: lastUpdatedDate.getTime(),
    lastUpdatedIsNaN: isNaN(lastUpdatedDate.getTime())
  });

  // Check if dates are valid
  if (isNaN(firstSeenDate.getTime()) || isNaN(lastUpdatedDate.getTime())) {
    console.error('[TimelineBar] Invalid date values after parsing', {
      firstSeenDate,
      lastUpdatedDate
    });
    // Render placeholder bar for invalid dates
    return (
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full opacity-40" title="Invalid date format" />
    );
  }
  
  // Calculate total timeline duration in milliseconds
  const totalDuration = latest.getTime() - earliest.getTime();
  
  console.log('[TimelineBar] Timeline bounds:', {
    totalDuration,
    earliestTime: earliest.getTime(),
    latestTime: latest.getTime()
  });
  
  // Avoid division by zero
  if (totalDuration === 0) {
    console.warn('[TimelineBar] Total duration is zero, rendering placeholder');
    return (
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full" title={tooltipText} />
    );
  }
  
  // Calculate start and end positions as percentages
  const startPosition = ((firstSeenDate.getTime() - earliest.getTime()) / totalDuration) * 100;
  const endPosition = ((lastUpdatedDate.getTime() - earliest.getTime()) / totalDuration) * 100;
  
  // DEBUG: Log position calculations
  console.log('[TimelineBar] Position calculations:', {
    startPosition,
    startPositionIsNaN: isNaN(startPosition),
    startPositionIsNegative: startPosition < 0,
    endPosition,
    endPositionIsNaN: isNaN(endPosition),
    endPositionIsNegative: endPosition < 0,
    startGreaterThanEnd: startPosition > endPosition
  });
  
  // Clamp values between 0 and 100
  const clampedStart = Math.max(0, Math.min(100, startPosition));
  const clampedEnd = Math.max(0, Math.min(100, endPosition));
  
  // Calculate width of the filled section
  const width = clampedEnd - clampedStart;
  
  // DEBUG: Log final bar dimensions with detailed info
  console.log('[TimelineBar] Final bar dimensions:', {
    clampedStart,
    clampedEnd,
    width,
    widthIsNaN: isNaN(width),
    widthIsZero: width === 0,
    widthIsNegative: width < 0,
    clampedEndLessThanStart: clampedEnd < clampedStart,
    firstSeenTime: firstSeenDate.getTime(),
    lastUpdatedTime: lastUpdatedDate.getTime(),
    firstSeenAfterLastUpdated: firstSeenDate.getTime() > lastUpdatedDate.getTime()
  });

  // Check if width is invalid for rendering
  if (isNaN(width) || width <= 0) {
    console.warn('[TimelineBar] Invalid bar width, rendering placeholder', { 
      width,
      reason: width < 0 ? 'Negative width (last_updated before first_seen?)' : 'Zero or NaN width'
    });
    return (
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full opacity-40" title="Invalid bar width" />
    );
  }
  
  // Determine color based on lifecycle state
  const getColorClass = (state?: string): string => {
    switch (state) {
      case 'emerging':
      case 'rising':
        return 'bg-green-500';
      case 'hot':
      case 'heating':
        return 'bg-red-500';
      case 'mature':
        return 'bg-blue-500';
      case 'cooling':
        return 'bg-gray-400';
      default:
        return 'bg-blue-500';
    }
  };
  
  // Determine opacity based on article count (activity density)
  const getOpacityClass = (articleCount: number, maxCount: number): string => {
    if (maxCount === 0) return 'opacity-60';
    
    const ratio = articleCount / maxCount;
    
    if (ratio >= 0.7) return 'opacity-100'; // High activity
    if (ratio >= 0.3) return 'opacity-60';  // Medium activity
    return 'opacity-30';                     // Low activity
  };
  
  const colorClass = getColorClass(lifecycle_state);
  
  // If timeline_data is provided, render segments with activity density shading
  if (timeline_data && timeline_data.length > 0) {
    console.log('[TimelineBar] Timeline data provided, rendering segments:', {
      timelineDataLength: timeline_data.length,
      timelineData: timeline_data
    });

    // Filter timeline data to only include points within the narrative's active period
    const activeTimelineData = timeline_data.filter(point => {
      const pointDate = new Date(point.date);
      return pointDate >= firstSeenDate && pointDate <= lastUpdatedDate;
    });
    
    console.log('[TimelineBar] Filtered active timeline data:', {
      activeDataLength: activeTimelineData.length,
      activeData: activeTimelineData
    });
    
    if (activeTimelineData.length === 0) {
      // Fallback to solid bar if no data points in range
      console.warn('[TimelineBar] No active timeline data points in range, rendering solid bar');
      return (
        <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full relative overflow-hidden" title={tooltipText}>
          <div 
            className={`absolute h-full ${colorClass} opacity-60 rounded-full transition-all duration-300`}
            style={{
              left: `${clampedStart}%`,
              width: `${width}%`
            }}
          />
        </div>
      );
    }
    
    // Find max article count for normalization
    const maxArticleCount = Math.max(...activeTimelineData.map(d => d.article_count));
    console.log('[TimelineBar] Max article count for normalization:', maxArticleCount);
    
    // Create segments based on timeline data points
    const segments = activeTimelineData.map((point, index) => {
      const pointDate = new Date(point.date);
      const pointPosition = ((pointDate.getTime() - earliest.getTime()) / totalDuration) * 100;
      
      // Calculate segment width (distance to next point or end of narrative)
      let segmentWidth: number;
      if (index < activeTimelineData.length - 1) {
        const nextPointDate = new Date(activeTimelineData[index + 1].date);
        const nextPosition = ((nextPointDate.getTime() - earliest.getTime()) / totalDuration) * 100;
        segmentWidth = nextPosition - pointPosition;
      } else {
        // Last segment extends to the end of the narrative
        segmentWidth = clampedEnd - pointPosition;
      }
      
      const opacityClass = getOpacityClass(point.article_count, maxArticleCount);
      
      console.log(`[TimelineBar] Segment ${index}:`, {
        pointPosition,
        segmentWidth,
        segmentWidthIsNaN: isNaN(segmentWidth),
        segmentWidthIsNegative: segmentWidth < 0,
        opacityClass,
        articleCount: point.article_count
      });
      
      return {
        left: pointPosition,
        width: segmentWidth,
        opacity: opacityClass,
        articleCount: point.article_count
      };
    });
    
    console.log('[TimelineBar] Rendering segments:', segments);

    return (
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full relative overflow-hidden" title={tooltipText}>
        {/* Render each segment with its own opacity */}
        {segments.map((segment, index) => (
          <div
            key={index}
            className={`absolute h-full ${colorClass} ${segment.opacity} transition-all duration-300`}
            style={{
              left: `${segment.left}%`,
              width: `${segment.width}%`
            }}
          />
        ))}
      </div>
    );
  }
  
  // Fallback: render solid bar without activity density shading
  return (
    <div className="w-full h-1 bg-gray-200 dark:bg-gray-700 rounded-full relative overflow-hidden" title={tooltipText}>
      {/* Filled section representing narrative timeline */}
      <div 
        className={`absolute h-full ${colorClass} rounded-full transition-all duration-300`}
        style={{
          left: `${clampedStart}%`,
          width: `${width}%`
        }}
      />
    </div>
  );
};

/**
 * Calculate timeline bounds from narratives array
 * Returns the earliest first_seen date and the latest date (current time or max last_updated)
 */
const calculateTimelineBounds = (narratives: any[]): { earliest: Date; latest: Date } => {
  if (!narratives || narratives.length === 0) {
    const now = new Date();
    return { earliest: now, latest: now };
  }

  let earliest = new Date();
  let latest = new Date();

  narratives.forEach((narrative) => {
    // Get first_seen date
    if (narrative.first_seen) {
      try {
        const firstSeenDate = new Date(parseNarrativeDate(narrative.first_seen));
        if (!isNaN(firstSeenDate.getTime()) && firstSeenDate < earliest) {
          earliest = firstSeenDate;
        }
      } catch {
        // Skip invalid dates
      }
    }

    // Get last_updated date
    const lastUpdated = narrative.last_updated || narrative.updated_at;
    if (lastUpdated) {
      try {
        const lastUpdatedDate = new Date(parseNarrativeDate(lastUpdated));
        if (!isNaN(lastUpdatedDate.getTime()) && lastUpdatedDate > latest) {
          latest = lastUpdatedDate;
        }
      } catch {
        // Skip invalid dates
      }
    }
  });

  // Ensure latest is at least the current time
  const now = new Date();
  if (latest < now) {
    latest = now;
  }

  return { earliest, latest };
};

export function Narratives() {
  const [expandedArticles, setExpandedArticles] = useState<Set<number>>(new Set());
  const [narrativeArticles, setNarrativeArticles] = useState<Map<string, any[]>>(new Map());
  const [loadingArticles, setLoadingArticles] = useState<Set<string>>(new Set());
  
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['narratives'],
    queryFn: async () => {
      const result = await narrativesAPI.getNarratives();
      console.log('[DEBUG] API returned:', result.length, 'narratives');
      return result;
    },
    refetchInterval: 60000, // 60 seconds
  });

  const narratives = data || [];
  
  // Calculate timeline bounds for visual timeline
  const timelineBounds = calculateTimelineBounds(narratives);

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Active Narratives
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Clustered stories and trending topics in the crypto space
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Last updated: {formatRelativeTime(parseNarrativeDate(dataUpdatedAt))}
          </p>
        )}
      </div>

      {/* Timeline Header */}
      <TimelineHeader earliest={timelineBounds.earliest} latest={timelineBounds.latest} />

      <div className="space-y-6">
        {narratives.map((narrative, index) => {
          // Handle both old and new field names for backward compatibility
          const displayTitle = narrative.title || narrative.theme;
          const displaySummary = narrative.summary || narrative.story;
          
          // IMPORTANT: Use last_article_at as primary timestamp for "Updated X ago"
          // - last_article_at = when the most recent article was published (meaningful for users)
          // - last_updated = when background worker last processed narrative (not meaningful - all show "just now")
          // - updated_at = legacy field, fallback for backward compatibility
          const displayUpdated = narrative.last_article_at || narrative.last_updated || narrative.updated_at;
          const isExpanded = expandedArticles.has(index);
          const narrativeId = narrative._id || '';
          const articles = narrativeArticles.get(narrativeId) || narrative.articles || [];
          const isLoadingArticles = loadingArticles.has(narrativeId);
          
          const toggleExpanded = async () => {
            console.log('[DEBUG] Card clicked - Narrative ID:', narrativeId, 'Title:', displayTitle);
            const newExpanded = new Set(expandedArticles);
            if (newExpanded.has(index)) {
              console.log('[DEBUG] Collapsing card at index:', index);
              newExpanded.delete(index);
            } else {
              console.log('[DEBUG] Expanding card at index:', index);
              newExpanded.add(index);
              
              // Fetch articles if not already loaded
              if (narrativeId && !narrativeArticles.has(narrativeId) && !loadingArticles.has(narrativeId)) {
                console.log('[DEBUG] Fetching articles for narrative:', narrativeId);
                setLoadingArticles(prev => new Set(prev).add(narrativeId));
                try {
                  const narrativeWithArticles = await narrativesAPI.getNarrativeById(narrativeId);
                  console.log('[DEBUG] API Response:', narrativeWithArticles);
                  console.log('[DEBUG] Articles in response:', narrativeWithArticles.articles?.length || 0);
                  setNarrativeArticles(prev => new Map(prev).set(narrativeId, narrativeWithArticles.articles || []));
                } catch (error) {
                  console.error('[ERROR] Failed to fetch articles:', error);
                } finally {
                  setLoadingArticles(prev => {
                    const next = new Set(prev);
                    next.delete(narrativeId);
                    return next;
                  });
                }
              } else {
                console.log('[DEBUG] Skipping article fetch - narrativeId:', narrativeId, 'already has articles:', narrativeArticles.has(narrativeId));
              }
            }
            setExpandedArticles(newExpanded);
          };
          
          return (
          <Card 
            key={`${narrative.theme}-${index}`}
          >
            <div onClick={toggleExpanded}>
            <CardHeader>
              {/* Title and Lifecycle badge in same row */}
              <div className="flex items-start justify-between gap-3">
                <CardTitle>{displayTitle}</CardTitle>
                
                {/* Lifecycle badge */}
                {(() => {
                  const lifecycleValue = narrative.lifecycle_state || narrative.lifecycle;
                  const config = lifecycleValue && lifecycleConfig[lifecycleValue as keyof typeof lifecycleConfig];
                  if (!config) return null;
                  
                  const Icon = config.icon;
                  
                  // Define gradient styles for each lifecycle state
                  const gradientStyles: Record<string, string> = {
                    emerging: 'text-white bg-gradient-to-r from-blue-500 to-indigo-500 dark:from-blue-600 dark:to-indigo-600 shadow-sm',
                    rising: 'text-white bg-gradient-to-r from-green-500 to-emerald-500 dark:from-green-600 dark:to-emerald-600 shadow-sm',
                    hot: 'text-white bg-gradient-to-r from-orange-500 to-red-500 dark:from-orange-600 dark:to-red-600 shadow-sm',
                    heating: 'text-white bg-gradient-to-r from-red-500 to-pink-500 dark:from-red-600 dark:to-pink-600 shadow-sm',
                    mature: 'text-white bg-gradient-to-r from-purple-500 to-violet-500 dark:from-purple-600 dark:to-violet-600 shadow-sm',
                    cooling: 'text-white bg-gradient-to-r from-gray-500 to-slate-500 dark:from-gray-600 dark:to-slate-600 shadow-sm',
                  };
                  
                  const gradientClass = gradientStyles[lifecycleValue as string] || `text-${config.color} bg-${config.color}/10 dark:bg-${config.color}/20`;
                  
                  return (
                    <span className={cn(
                      'flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-full whitespace-nowrap',
                      gradientClass
                    )}>
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </span>
                  );
                })()}
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

              {/* Timeline Bar */}
              <div className="mb-4">
                <TimelineBar
                  first_seen={narrative.first_seen}
                  last_updated={displayUpdated}
                  earliest={timelineBounds.earliest}
                  latest={timelineBounds.latest}
                  lifecycle_state={narrative.lifecycle_state || narrative.lifecycle}
                  timeline_data={narrative.timeline_data}
                  tooltipText={`Started: ${formatFullTimestamp(narrative.first_seen)} • Updated: ${formatFullTimestamp(displayUpdated)}`}
                />
                {/* Combined date label */}
                <div className="text-xs text-gray-600 dark:text-gray-400 mt-2 text-center">
                  {formatDate(narrative.first_seen)} → {formatShortRelativeTime(displayUpdated)}
                </div>
              </div>

              {/* Articles section */}
              {(narrative.article_count > 0 || articles.length > 0) && (
                <div className="pt-4 border-t border-gray-200 dark:border-dark-border">
                  <div className="text-sm text-blue-600 dark:text-blue-400 font-medium flex items-center gap-1">
                    {isExpanded ? '▼' : '▶'} {formatNumber(narrative.article_count)} Articles
                  </div>
                  
                  {isExpanded && (() => {
                    console.log('[DEBUG] Rendering expanded article section - isLoadingArticles:', isLoadingArticles, 'articles.length:', articles.length);
                    return (
                    <div className="mt-3 space-y-2">
                      {isLoadingArticles ? (
                        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                          Loading articles...
                        </div>
                      ) : articles.length > 0 ? (
                        articles.map((article, articleIdx) => {
                          console.log('[DEBUG] Rendering article:', articleIdx, article.title);
                          return (
                          <div key={articleIdx} className="text-sm bg-gray-50 dark:bg-dark-hover p-3 rounded">
                            <a
                              href={article.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline font-medium block mb-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {article.title}
                            </a>
                            <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400 text-xs">
                              <span className="capitalize">{article.source}</span>
                              <span>•</span>
                              <span>{formatRelativeTime(article.published_at)}</span>
                            </div>
                          </div>
                          );
                        })
                      ) : (
                        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                          No articles available
                        </div>
                      )}
                    </div>
                    );
                  })()}
                </div>
              )}
            </CardContent>
            </div>
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
