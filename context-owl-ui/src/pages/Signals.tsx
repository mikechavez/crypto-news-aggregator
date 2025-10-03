import { useQuery } from '@tanstack/react-query';
import { signalsAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, getSignalStrengthColor, formatPercentage } from '../lib/formatters';
import { Link } from 'react-router-dom';

export function Signals() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['signals'],
    queryFn: () => signalsAPI.getSignals({ limit: 50 }),
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
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {data?.signals.map((signal) => (
          <Card key={signal.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-lg">
                  {signal.entity?.name || `Entity #${signal.entity_id}`}
                </CardTitle>
                <span
                  className={`text-sm font-semibold ${getSignalStrengthColor(signal.strength)}`}
                >
                  {formatPercentage(signal.strength, 0)}
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Type:</span>
                  <span className="font-medium text-gray-900 capitalize">
                    {signal.signal_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">Detected:</span>
                  <span className="text-gray-700">
                    {formatRelativeTime(signal.detected_at)}
                  </span>
                </div>
                {signal.context && Object.keys(signal.context).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs text-gray-500 mb-1">Context:</p>
                    <div className="text-xs text-gray-700 space-y-1">
                      {Object.entries(signal.context).slice(0, 3).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-gray-500">{key}:</span>
                          <span className="font-medium">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="mt-4">
                  <Link
                    to={`/entity/${signal.entity_id}`}
                    className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                  >
                    View Details →
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data?.signals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No signals detected yet</p>
        </div>
      )}
    </div>
  );
}
