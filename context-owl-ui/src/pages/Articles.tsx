import { useQuery } from '@tanstack/react-query';
import { articlesAPI } from '../api';
import { Card, CardHeader, CardTitle, CardContent } from '../components/Card';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';
import { formatRelativeTime, getEntityTypeColor } from '../lib/formatters';

const getSourceColor = (source: string): string => {
  const sourceColors: Record<string, string> = {
    twitter: 'bg-blue-100 text-blue-700',
    telegram: 'bg-cyan-100 text-cyan-700',
    rss: 'bg-orange-100 text-orange-700',
    coindesk: 'bg-purple-100 text-purple-700',
    cointelegraph: 'bg-pink-100 text-pink-700',
    decrypt: 'bg-green-100 text-green-700',
    bitcoinmagazine: 'bg-yellow-100 text-yellow-700',
  };
  return sourceColors[source.toLowerCase()] || 'bg-gray-100 text-gray-700';
};

export function Articles() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', 'recent'],
    queryFn: () => articlesAPI.getRecent(100),
    refetchInterval: 60000, // Refetch every minute
  });

  if (isLoading) {
    return <Loading />;
  }

  if (error) {
    return <ErrorMessage message={error instanceof Error ? error.message : 'Failed to load articles'} />;
  }

  const articles = data?.articles || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Recent Articles</h1>
          <p className="text-gray-600 mt-1">
            Last {articles.length} articles in chronological order
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Article Feed</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Entities
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                      {formatRelativeTime(article.published_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1 group"
                      >
                        <span className="line-clamp-2">{article.title}</span>
                        <svg className="w-3 h-3 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </a>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSourceColor(article.source)}`}>
                        {article.source}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {article.entities.slice(0, 3).map((entity, idx) => (
                          <span
                            key={idx}
                            className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getEntityTypeColor(entity.type)}`}
                          >
                            {entity.name}
                          </span>
                        ))}
                        {article.entities.length > 3 && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                            +{article.entities.length - 3} more
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {articles.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              No articles found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
