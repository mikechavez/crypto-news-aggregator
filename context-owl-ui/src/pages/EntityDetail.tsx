import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { entitiesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import {
  formatRelativeTime,
  formatSentiment,
  getSentimentColor,
  getSignalStrengthColor,
  formatPercentage,
} from '../lib/formatters';

export function EntityDetail() {
  const { id } = useParams<{ id: string }>();
  const entityId = parseInt(id || '0', 10);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['entity', entityId],
    queryFn: () => entitiesAPI.getEntityDetail(entityId),
    enabled: !!entityId,
  });

  if (isLoading) return <Loading />;
  if (error) return <ErrorMessage message={error.message} onRetry={() => refetch()} />;
  if (!data) return <ErrorMessage message="Entity not found" />;

  return (
    <div>
      <div className="mb-8">
        <Link to="/" className="text-blue-600 hover:text-blue-800 text-sm mb-2 inline-block">
          ← Back to Signals
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">{data.entity.name}</h1>
        <p className="mt-2 text-gray-600 capitalize">
          {data.entity.entity_type.replace(/_/g, ' ')}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Signals */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Signals</CardTitle>
          </CardHeader>
          <CardContent>
            {data.signals.length > 0 ? (
              <div className="space-y-4">
                {data.signals.map((signal, index) => (
                  <div key={`${signal.entity}-${index}`} className="border-b border-gray-200 pb-3 last:border-0">
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-sm font-medium text-gray-900 capitalize">
                        {signal.entity_type.replace(/_/g, ' ')}
                      </span>
                      <span className={`text-sm font-semibold ${getSignalStrengthColor(signal.signal_score)}`}>
                        {formatPercentage(signal.signal_score, 0)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      {formatRelativeTime(signal.last_updated)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No signals detected</p>
            )}
          </CardContent>
        </Card>

        {/* Mentions */}
        <Card>
          <CardHeader>
            <CardTitle>Article Mentions</CardTitle>
          </CardHeader>
          <CardContent>
            {data.mentions.length > 0 ? (
              <div className="space-y-4">
                {data.mentions.slice(0, 5).map((mention) => (
                  <div key={mention.id} className="border-b border-gray-200 pb-3 last:border-0">
                    <div className="flex items-start justify-between mb-2">
                      <span className="text-sm text-gray-700">
                        {mention.mention_count} mention{mention.mention_count > 1 ? 's' : ''}
                      </span>
                      {mention.sentiment_score !== null && (
                        <span className={`text-sm font-medium ${getSentimentColor(mention.sentiment_score)}`}>
                          {formatSentiment(mention.sentiment_score)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      {formatRelativeTime(mention.created_at)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No mentions found</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Articles */}
      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Articles</CardTitle>
          </CardHeader>
          <CardContent>
            {data.recent_articles.length > 0 ? (
              <div className="space-y-4">
                {data.recent_articles.map((article) => (
                  <div key={article.id} className="border-b border-gray-200 pb-4 last:border-0">
                    <a
                      href={article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 font-medium mb-2 block"
                    >
                      {article.title}
                    </a>
                    {article.summary && (
                      <p className="text-sm text-gray-700 mb-2">{article.summary}</p>
                    )}
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span>{article.source}</span>
                      <span>{formatRelativeTime(article.published_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm">No recent articles</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
