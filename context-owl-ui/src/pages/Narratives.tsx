import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, TrendingUp, Flame, Zap, Star, Wind, LayoutGrid, Activity, Archive, RotateCcw, FileText, Users } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['narratives', viewMode],
    queryFn: () => viewMode === 'archive' ? narrativesAPI.getResurrectedNarratives(20, 7) : narrativesAPI.getNarratives(),
    refetchInterval: 60000, // 60 seconds
  });

  const narratives = data || [];

  // Calculate date range from narratives for the timeline scrubber
  const dateRange = useMemo(() => {
    if (narratives.length === 0) {
      return { minDate: new Date(), maxDate: new Date(), totalDays: 0 };
    }

    const dates = narratives.flatMap(narrative => {
      const firstSeen = narrative.first_seen ? new Date(narrative.first_seen) : new Date();
      const lastUpdated = narrative.last_updated ? new Date(narrative.last_updated) : new Date();
      return [firstSeen, lastUpdated];
    });

    const minDate = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())));
    const totalDays = Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24));

    return { minDate, maxDate, totalDays };
  }, [narratives]);

  // Calculate activity by day for heatmap
  const activityByDay = useMemo(() => {
    if (narratives.length === 0 || dateRange.totalDays === 0) {
      return [];
    }

    const activityMap = new Map<string, number>();
    
    // For each day in the range, count how many narratives were active
    for (let i = 0; i <= dateRange.totalDays; i++) {
      const currentDate = new Date(dateRange.minDate.getTime() + i * 24 * 60 * 60 * 1000);
      const dateKey = currentDate.toISOString().split('T')[0];
      
      const count = narratives.filter(narrative => {
        const firstSeen = narrative.first_seen ? new Date(narrative.first_seen) : null;
        const lastUpdated = narrative.last_updated ? new Date(narrative.last_updated) : null;
        
        if (!firstSeen || !lastUpdated) return false;
        
        // Check if currentDate is between first_seen and last_updated
        return currentDate >= firstSeen && currentDate <= lastUpdated;
      }).length;
      
      activityMap.set(dateKey, count);
    }
    
    // Convert to array with date and count
    return Array.from(activityMap.entries()).map(([dateKey, count]) => ({
      date: new Date(dateKey),
      count
    }));
  }, [narratives, dateRange]);

  // Calculate max activity for color scaling
  const maxActivity = useMemo(() => {
    return Math.max(...activityByDay.map(d => d.count), 1);
  }, [activityByDay]);

  // Filter narratives based on selected date
  const filteredNarratives = useMemo(() => {
    if (!selectedDate || viewMode !== 'pulse') {
      return narratives;
    }

    return narratives.filter(narrative => {
      const firstSeen = narrative.first_seen ? new Date(narrative.first_seen) : null;
      const lastUpdated = narrative.last_updated ? new Date(narrative.last_updated) : null;
      
      if (!firstSeen || !lastUpdated) return false;
      
      // Check if selectedDate is between first_seen and last_updated
      return selectedDate >= firstSeen && selectedDate <= lastUpdated;
    });
  }, [narratives, selectedDate, viewMode]);

  // Calculate dynamic stats for the selected date
  const dateStats = useMemo(() => {
    const activeNarratives = viewMode === 'pulse' ? filteredNarratives : narratives;
    
    // Total narratives
    const total = activeNarratives.length;
    
    // Breakdown by lifecycle state
    const lifecycleBreakdown = activeNarratives.reduce((acc, narrative) => {
      const state = narrative.lifecycle_state || narrative.lifecycle || 'unknown';
      acc[state] = (acc[state] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    // Most active entity (entity appearing in most narratives)
    const entityCounts = new Map<string, number>();
    activeNarratives.forEach(narrative => {
      narrative.entities.forEach(entity => {
        entityCounts.set(entity, (entityCounts.get(entity) || 0) + 1);
      });
    });
    
    let mostActiveEntity = 'None';
    let maxCount = 0;
    entityCounts.forEach((count, entity) => {
      if (count > maxCount) {
        maxCount = count;
        mostActiveEntity = entity;
      }
    });
    
    // Average article count per narrative
    const totalArticles = activeNarratives.reduce((sum, n) => sum + (n.article_count || 0), 0);
    const avgArticles = total > 0 ? (totalArticles / total).toFixed(1) : '0';
    
    return {
      total,
      lifecycleBreakdown,
      mostActiveEntity,
      avgArticles
    };
  }, [filteredNarratives, narratives, viewMode]);

  // Format date for display
  const formatDateForDisplay = (date: Date) => {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Get color for activity level (gradient from gray to red/orange)
  const getActivityColor = (count: number, max: number) => {
    if (count === 0) return 'bg-gray-200 dark:bg-gray-700';
    
    const intensity = count / max;
    
    if (intensity < 0.25) return 'bg-orange-200 dark:bg-orange-900/40';
    if (intensity < 0.5) return 'bg-orange-300 dark:bg-orange-800/60';
    if (intensity < 0.75) return 'bg-orange-400 dark:bg-orange-700/80';
    return 'bg-red-500 dark:bg-red-600';
  };

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
          {/* Timeline Scrubber */}
          <div className="mb-8 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Timeline Filter
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {selectedDate 
                    ? `Showing narratives active on ${formatDateForDisplay(selectedDate)}`
                    : 'Showing all current narratives'
                  }
                </p>
              </div>
              {selectedDate && (
                <button
                  onClick={() => setSelectedDate(null)}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset to Current
                </button>
              )}
            </div>

            {/* Activity Heatmap */}
            {activityByDay.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Activity by Day
                </h4>
                <div className="flex items-end h-16 gap-0.5">
                  {activityByDay.map((day, index) => {
                    const heightPercent = (day.count / maxActivity) * 100;
                    const isSelected = selectedDate && 
                      day.date.toDateString() === selectedDate.toDateString();
                    
                    return (
                      <button
                        key={index}
                        onClick={() => setSelectedDate(day.date)}
                        className={cn(
                          'flex-1 transition-all duration-200 rounded-t hover:opacity-80 relative group',
                          getActivityColor(day.count, maxActivity),
                          isSelected && 'ring-2 ring-blue-600 ring-offset-2 dark:ring-offset-gray-900'
                        )}
                        style={{ height: `${Math.max(heightPercent, 5)}%` }}
                        title={`${formatDateForDisplay(day.date)}: ${day.count} narratives`}
                      >
                        {/* Tooltip on hover */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
                          {formatDateForDisplay(day.date)}: {day.count}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {dateRange.totalDays > 0 && (
              <div className="relative">
                {/* Date labels */}
                <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-2">
                  <span>{formatDateForDisplay(dateRange.minDate)}</span>
                  <span>{formatDateForDisplay(dateRange.maxDate)}</span>
                </div>

                {/* Slider container */}
                <div className="relative h-12 flex items-center">
                  {/* Gradient track */}
                  <div className="absolute inset-x-0 h-2 bg-gradient-to-r from-blue-300 via-indigo-400 to-purple-500 dark:from-blue-600 dark:via-indigo-700 dark:to-purple-800 rounded-full" />
                  
                  {/* Range input */}
                  <input
                    type="range"
                    min="0"
                    max={activityByDay.length - 1}
                    step="1"
                    value={selectedDate 
                      ? activityByDay.findIndex(day => day.date.toDateString() === selectedDate.toDateString())
                      : activityByDay.length - 1
                    }
                    onChange={(e) => {
                      const index = parseInt(e.target.value);
                      if (index >= 0 && index < activityByDay.length) {
                        setSelectedDate(activityByDay[index].date);
                      }
                    }}
                    className="absolute inset-x-0 w-full h-12 opacity-0 cursor-pointer z-10"
                    style={{ margin: 0 }}
                  />

                  {/* Custom thumb */}
                  <div 
                    className="absolute w-6 h-6 bg-white dark:bg-gray-800 border-4 border-blue-600 dark:border-blue-400 rounded-full shadow-lg pointer-events-none transition-all duration-200"
                    style={{
                      left: (() => {
                        const index = selectedDate 
                          ? activityByDay.findIndex(day => day.date.toDateString() === selectedDate.toDateString())
                          : activityByDay.length - 1;
                        const totalBars = activityByDay.length;
                        // Calculate position to center on each bar
                        const barWidth = 100 / totalBars;
                        const centerOffset = barWidth / 2;
                        const position = (index * barWidth) + centerOffset;
                        return `calc(${position}% - 12px)`;
                      })()
                    }}
                  />
                </div>

                {/* Selected date display */}
                {selectedDate && (
                  <div 
                    className="absolute -bottom-8 bg-blue-600 dark:bg-blue-500 text-white px-3 py-1 rounded-full text-xs font-semibold shadow-lg"
                    style={{
                      left: (() => {
                        const index = activityByDay.findIndex(day => day.date.toDateString() === selectedDate.toDateString());
                        const totalBars = activityByDay.length;
                        const barWidth = 100 / totalBars;
                        const centerOffset = barWidth / 2;
                        const position = (index * barWidth) + centerOffset;
                        return `calc(${position}% - 40px)`;
                      })()
                    }}
                  >
                    {formatDateForDisplay(selectedDate)}
                  </div>
                )}
              </div>
            )}

            {/* Results count */}
            <div className="mt-10 text-sm text-gray-600 dark:text-gray-400">
              {selectedDate 
                ? `${filteredNarratives.length} of ${narratives.length} narratives active on this date`
                : `${narratives.length} total narratives`
              }
            </div>
          </div>

          {/* Dynamic Stats Panel */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {selectedDate ? `Stats for ${formatDateForDisplay(selectedDate)}` : 'Right Now'}
              </h3>
            </div>
            
            <AnimatePresence mode="wait">
              <motion.div 
                key={selectedDate ? selectedDate.toISOString() : 'current'}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
              >
                {/* Total Narratives */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, delay: 0 }}
                >
                  <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-blue-600 dark:bg-blue-500 rounded-lg">
                          <TrendingUp className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <div className="text-3xl font-bold text-blue-900 dark:text-blue-100">
                            {dateStats.total}
                          </div>
                          <div className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                            Total Narratives
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Lifecycle Breakdown */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, delay: 0.1 }}
                >
                  <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-indigo-600 dark:bg-indigo-500 rounded-lg">
                          <Activity className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="text-sm text-indigo-700 dark:text-indigo-300 font-medium mb-2">
                            Lifecycle States
                          </div>
                          <div className="space-y-1">
                            {Object.entries(dateStats.lifecycleBreakdown)
                              .sort(([, a], [, b]) => b - a)
                              .slice(0, 3)
                              .map(([state, count]) => (
                                <div key={state} className="flex items-center justify-between text-xs">
                                  <span className="text-indigo-800 dark:text-indigo-200 capitalize">
                                    {state}
                                  </span>
                                  <span className="font-bold text-indigo-900 dark:text-indigo-100">
                                    {count}
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Most Active Entity */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, delay: 0.2 }}
                >
                  <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-purple-600 dark:bg-purple-500 rounded-lg">
                          <Users className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm text-purple-700 dark:text-purple-300 font-medium mb-1">
                            Most Active Entity
                          </div>
                          <div className="text-lg font-bold text-purple-900 dark:text-purple-100 truncate">
                            {dateStats.mostActiveEntity}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                {/* Average Article Count */}
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, delay: 0.3 }}
                >
                  <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-blue-200 dark:border-blue-800">
                    <CardContent className="pt-6">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-green-600 dark:bg-green-500 rounded-lg">
                          <FileText className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <div className="text-3xl font-bold text-green-900 dark:text-green-100">
                            {dateStats.avgArticles}
                          </div>
                          <div className="text-sm text-green-700 dark:text-green-300 font-medium">
                            Avg Articles/Narrative
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </motion.div>
            </AnimatePresence>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={selectedDate ? selectedDate.toISOString() : 'current'}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <TimelineView narratives={filteredNarratives || []} selectedDate={selectedDate} />
            </motion.div>
          </AnimatePresence>
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
