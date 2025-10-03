import { useQuery } from '@tanstack/react-query';
import { narrativesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, formatNumber } from '../lib/formatters';

export function Narratives() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['narratives'],
    queryFn: () => narrativesAPI.getNarratives({ limit: 50 }),
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Emerging Narratives</h1>
        <p className="mt-2 text-gray-600">
          Clustered stories and trending topics in the crypto space
        </p>
      </div>

      <div className="space-y-6">
        {data?.narratives.map((narrative) => (
          <Card key={narrative.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle>{narrative.title}</CardTitle>
                <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full">
                  {formatNumber(narrative.article_count)} articles
                </span>
              </div>
            </CardHeader>
            <CardContent>
              {narrative.description && (
                <p className="text-gray-700 mb-4">{narrative.description}</p>
              )}
              
              <div className="flex flex-wrap gap-2 mb-4">
                {narrative.keywords.slice(0, 10).map((keyword, idx) => (
                  <span
                    key={idx}
                    className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>

              <div className="flex items-center justify-between text-sm text-gray-500 pt-4 border-t border-gray-200">
                <span>Created {formatRelativeTime(narrative.created_at)}</span>
                <span>Updated {formatRelativeTime(narrative.updated_at)}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {data?.narratives.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No narratives detected yet</p>
        </div>
      )}
    </div>
  );
}
