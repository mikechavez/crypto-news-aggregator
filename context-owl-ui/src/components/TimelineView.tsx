import { useMemo, useState } from 'react';
import type { Narrative } from '../types';
import { format, differenceInDays, parseISO } from 'date-fns';
import { motion } from 'framer-motion';
import { Sparkles, TrendingUp, Flame, Zap, Star, Wind, X } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './Card';

interface TimelineRowProps {
  narrative: Narrative;
  dateRange: {
    minDate: Date;
    maxDate: Date;
    totalDays: number;
  };
  onNarrativeClick: (narrative: Narrative) => void;
  selectedDate?: Date | null;
}

interface TimelineViewProps {
  narratives: Narrative[];
  selectedDate?: Date | null;
}

/**
 * Find the lifecycle state that was active on a given date
 * Returns the most recent state entry before or on the selected date
 */
const getHistoricalLifecycleState = (
  narrative: Narrative,
  selectedDate: Date
): { state: string; isHistorical: boolean } => {
  const currentState = narrative.lifecycle_state || narrative.lifecycle || 'emerging';
  
  // If no lifecycle history, return current state
  if (!narrative.lifecycle_history || narrative.lifecycle_history.length === 0) {
    return { state: currentState, isHistorical: false };
  }

  // Find the most recent state entry before or on selectedDate
  const historicalEntry = narrative.lifecycle_history
    .filter(entry => parseISO(entry.timestamp) <= selectedDate)
    .sort((a, b) => parseISO(b.timestamp).getTime() - parseISO(a.timestamp).getTime())[0];

  if (!historicalEntry) {
    // Selected date is before any lifecycle history entries
    // Return the earliest state or current state
    const earliestEntry = narrative.lifecycle_history
      .sort((a, b) => parseISO(a.timestamp).getTime() - parseISO(b.timestamp).getTime())[0];
    return { state: earliestEntry?.state || currentState, isHistorical: false };
  }

  const isHistorical = historicalEntry.state !== currentState;
  return { state: historicalEntry.state, isHistorical };
};

const TimelineRow = ({ narrative, dateRange, onNarrativeClick, selectedDate }: TimelineRowProps) => {
  const startDate = parseISO(narrative.first_seen);
  const endDate = parseISO(narrative.last_updated);
  
  const startPercent = dateRange.totalDays > 0
    ? (differenceInDays(startDate, dateRange.minDate) / dateRange.totalDays) * 100
    : 0;
  
  const widthPercent = dateRange.totalDays > 0
    ? (differenceInDays(endDate, startDate) / dateRange.totalDays) * 100
    : 100;

  // Determine opacity based on article count
  const getOpacityClass = (count: number) => {
    if (count < 4) return 'opacity-60';
    if (count < 7) return 'opacity-75';
    return 'opacity-90';
  };

  // Calculate peak day (day with most articles)
  const peakData = useMemo(() => {
    if (!narrative.articles || narrative.articles.length === 0) {
      return null;
    }

    // Group articles by date
    const articlesByDate = new Map<string, number>();
    narrative.articles.forEach(article => {
      const date = format(parseISO(article.published_at), 'yyyy-MM-dd');
      articlesByDate.set(date, (articlesByDate.get(date) || 0) + 1);
    });

    // Find the day with most articles
    let peakDay = '';
    let maxCount = 0;
    articlesByDate.forEach((count, date) => {
      if (count > maxCount) {
        maxCount = count;
        peakDay = date;
      }
    });

    if (!peakDay) return null;

    // Calculate position relative to timeline bar
    const peakDate = parseISO(peakDay);
    const peakPercent = dateRange.totalDays > 0
      ? ((differenceInDays(peakDate, dateRange.minDate) - differenceInDays(startDate, dateRange.minDate)) / dateRange.totalDays) * 100
      : 0;

    return { peakPercent, maxCount };
  }, [narrative.articles, dateRange, startDate]);

  const lifecycleConfig = {
    emerging: { Icon: Sparkles, iconColor: 'text-blue-500', barColor: 'bg-blue-500', gradientColor: 'from-blue-400 to-blue-600', label: 'Emerging' },
    rising: { Icon: TrendingUp, iconColor: 'text-green-500', barColor: 'bg-green-500', gradientColor: 'from-blue-500 to-green-500', label: 'Rising' },
    hot: { Icon: Flame, iconColor: 'text-orange-500', barColor: 'bg-orange-500', gradientColor: 'from-orange-400 to-orange-600', label: 'Hot' },
    heating: { Icon: Zap, iconColor: 'text-red-500', barColor: 'bg-red-500', gradientColor: 'from-red-400 to-red-600', label: 'Heating' },
    mature: { Icon: Star, iconColor: 'text-purple-500', barColor: 'bg-purple-500', gradientColor: 'from-purple-400 to-purple-600', label: 'Mature' },
    cooling: { Icon: Wind, iconColor: 'text-gray-500', barColor: 'bg-gray-500', gradientColor: 'from-gray-400 to-gray-600', label: 'Cooling' },
    dormant: { Icon: Wind, iconColor: 'text-gray-400', barColor: 'bg-gray-400', gradientColor: 'from-gray-300 to-gray-500', label: 'Dormant' },
  };

  // Determine which lifecycle state to display
  const currentState = narrative.lifecycle_state || narrative.lifecycle || 'emerging';
  let displayState = currentState;
  let isHistoricalState = false;
  
  if (selectedDate) {
    const historical = getHistoricalLifecycleState(narrative, selectedDate);
    displayState = historical.state;
    isHistoricalState = historical.isHistorical;
  }

  const { Icon, iconColor, gradientColor, label } = lifecycleConfig[displayState as keyof typeof lifecycleConfig] || lifecycleConfig.emerging;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="relative group px-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${iconColor}`} />
        <span className="text-sm font-medium text-gray-900 dark:text-white">
          {narrative.title}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          ({narrative.article_count} articles)
        </span>
        {/* Historical state indicator */}
        {isHistoricalState && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 font-medium">
            was {label}, now {lifecycleConfig[currentState as keyof typeof lifecycleConfig]?.label || currentState}
          </span>
        )}
        {narrative.entities && narrative.entities.length > 0 && (
          <>
            {narrative.entities.slice(0, 2).map((entity, index) => (
              <span
                key={index}
                className="text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
              >
                {entity}
              </span>
            ))}
          </>
        )}
      </div>
      <div className="relative h-12 bg-gray-100 dark:bg-dark-card rounded">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(widthPercent, 5)}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          onClick={() => onNarrativeClick(narrative)}
          className={`absolute h-full bg-gradient-to-r ${gradientColor} ${getOpacityClass(narrative.article_count)} rounded transition-all duration-300 cursor-pointer hover:scale-105`}
          style={{
            left: `${startPercent}%`,
          }}
        >
          {peakData && (
            <div
              className="absolute w-0 h-0 border-l-4 border-r-4 border-b-8 border-transparent border-b-white -top-2"
              style={{
                left: `${peakData.peakPercent}%`,
              }}
              title={`Peak: ${peakData.maxCount} articles`}
            />
          )}
        </motion.div>
        <div className="absolute left-0 top-full mt-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          <div className="bg-gray-900 dark:bg-gray-800 text-white text-xs rounded-lg p-3 shadow-lg min-w-[200px]">
            <div className="font-semibold mb-1">{narrative.title}</div>
            <div className="space-y-1 text-gray-300">
              <div>Start: {format(startDate, 'MMM d, yyyy')}</div>
              <div>Latest: {format(endDate, 'MMM d, yyyy')}</div>
              <div>Articles: {narrative.article_count}</div>
              <div>
                Stage: {label}
                {isHistoricalState && (
                  <span className="text-amber-300"> (historical, now {lifecycleConfig[currentState as keyof typeof lifecycleConfig]?.label || currentState})</span>
                )}
              </div>
              {narrative.mention_velocity && (
                <div>Velocity: {Math.round(narrative.mention_velocity)} per day</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export const TimelineView = ({ narratives, selectedDate }: TimelineViewProps) => {
  const [expandedNarrative, setExpandedNarrative] = useState<Narrative | null>(null);

  const dateRange = useMemo(() => {
    if (narratives.length === 0) {
      return { minDate: new Date(), maxDate: new Date(), totalDays: 0 };
    }

    const dates = narratives.flatMap(narrative => [
      parseISO(narrative.first_seen),
      parseISO(narrative.last_updated)
    ]);

    const minDate = new Date(Math.min(...dates.map(d => d.getTime())));
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())));
    const totalDays = differenceInDays(maxDate, minDate);

    return { minDate, maxDate, totalDays };
  }, [narratives]);

  return (
    <div className="space-y-4">
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 px-4 border-b border-gray-200 dark:border-dark-border pb-2">
        <span>{format(dateRange.minDate, 'MMM d')}</span>
        <span>{format(dateRange.maxDate, 'MMM d')}</span>
      </div>
      <div className="space-y-3">
        {narratives.map((narrative, index) => (
          <TimelineRow
            key={narrative._id || `${narrative.theme}-${narrative.title}-${index}`}
            narrative={narrative}
            dateRange={dateRange}
            onNarrativeClick={setExpandedNarrative}
            selectedDate={selectedDate}
          />
        ))}
      </div>

      {expandedNarrative && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={() => setExpandedNarrative(null)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <Card className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <CardHeader className="flex flex-row items-start justify-between">
              <div className="flex-1">
                <CardTitle className="text-2xl mb-2">{expandedNarrative.title}</CardTitle>
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  {(() => {
                    const lifecycleValue = expandedNarrative.lifecycle_state || expandedNarrative.lifecycle;
                    const gradientStyles: Record<string, string> = {
                      emerging: 'text-white bg-gradient-to-r from-blue-500 to-indigo-500 dark:from-blue-600 dark:to-indigo-600 shadow-lg shadow-blue-500/50 dark:shadow-blue-600/50',
                      rising: 'text-white bg-gradient-to-r from-green-500 to-emerald-500 dark:from-green-600 dark:to-emerald-600 shadow-lg shadow-green-500/50 dark:shadow-green-600/50',
                      hot: 'text-white bg-gradient-to-r from-orange-500 to-red-500 dark:from-orange-600 dark:to-red-600 shadow-lg shadow-orange-500/50 dark:shadow-orange-600/50',
                      heating: 'text-white bg-gradient-to-r from-red-500 to-pink-500 dark:from-red-600 dark:to-pink-600 shadow-lg shadow-red-500/50 dark:shadow-red-600/50',
                      mature: 'text-white bg-gradient-to-r from-purple-500 to-violet-500 dark:from-purple-600 dark:to-violet-600 shadow-lg shadow-purple-500/50 dark:shadow-purple-600/50',
                      cooling: 'text-white bg-gradient-to-r from-gray-500 to-slate-500 dark:from-gray-600 dark:to-slate-600 shadow-lg shadow-gray-500/50 dark:shadow-gray-600/50',
                    };
                    const gradientClass = gradientStyles[lifecycleValue as string] || 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300';
                    
                    return (
                      <span className={`px-3 py-1 rounded-full font-semibold ${gradientClass}`}>
                        {lifecycleValue}
                      </span>
                    );
                  })()}
                  <span>{expandedNarrative.article_count} articles</span>
                  <span>•</span>
                  <span>
                    {format(parseISO(expandedNarrative.first_seen), 'MMM d, yyyy')} - {format(parseISO(expandedNarrative.last_updated), 'MMM d, yyyy')}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setExpandedNarrative(null)}
                className="ml-4 p-1 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-gray-400 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white" />
              </button>
            </CardHeader>
            <CardContent className="space-y-6">
              {expandedNarrative.summary && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Summary</h3>
                  <p className="text-gray-700 dark:text-gray-300">{expandedNarrative.summary}</p>
                </div>
              )}

              {expandedNarrative.entities && expandedNarrative.entities.length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Related Entities</h3>
                  <div className="flex flex-wrap gap-2">
                    {expandedNarrative.entities.map((entity, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm"
                      >
                        {entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {expandedNarrative.articles && expandedNarrative.articles.length > 0 && (
                <div>
                  <h3 className="font-semibold text-lg mb-2">Articles ({expandedNarrative.articles.length})</h3>
                  <div className="space-y-3">
                    {expandedNarrative.articles.map((article, index) => (
                      <div
                        key={index}
                        className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                      >
                        <a
                          href={article.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                        >
                          {article.title}
                        </a>
                        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                          <span>{article.source}</span>
                          <span>•</span>
                          <span>{format(parseISO(article.published_at), 'MMM d, yyyy h:mm a')}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
          </div>
        </div>
      )}
    </div>
  );
};
