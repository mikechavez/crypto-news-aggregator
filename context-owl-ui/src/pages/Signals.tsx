import { useQuery } from '@tanstack/react-query';
import { signalsAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, getSignalStrengthColor, formatPercentage, formatSentiment, getSentimentColor } from '../lib/formatters';

export function Signals() {
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
                  <span className="font-medium text-gray-900 capitalize">
                    {signal.entity_type.replace(/_/g, ' ')}
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
