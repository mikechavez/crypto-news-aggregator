import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { signalsAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, getSignalStrengthColor, formatPercentage, formatSentiment, getSentimentColor, formatEntityType, getEntityTypeColor, formatTheme, getThemeColor } from '../lib/formatters';

export function Signals() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch, dataUpdatedAt } = useQuery({
    queryKey: ['signals'],
    queryFn: () => signalsAPI.getSignals({ limit: 10 }),
    refetchInterval: 30000, // 30 seconds
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Market Signals</h1>
        <p className="mt-2 text-gray-600">
          Real-time detection of unusual market activity and emerging trends
        </p>
        {dataUpdatedAt && (
          <p className="text-sm text-gray-500 mt-2">
            Last updated: {formatRelativeTime(new Date(dataUpdatedAt).toISOString())}
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
                    {formatRelativeTime(signal.last_updated)}
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
