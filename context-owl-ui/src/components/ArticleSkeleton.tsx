/**
 * ArticleSkeleton Component
 *
 * Animated skeleton placeholder for article cards during loading.
 * Matches the layout and dimensions of actual article cards.
 */
export function ArticleSkeleton() {
  return (
    <div className="bg-gray-50 dark:bg-dark-hover p-3 rounded animate-pulse">
      {/* Title skeleton - 75% width, varies for more natural look */}
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>

      {/* Metadata skeleton - Source, bullet, timestamp */}
      <div className="flex items-center gap-2">
        {/* Source name */}
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
        {/* Bullet separator */}
        <div className="h-3 w-1 bg-gray-200 dark:bg-gray-700 rounded"></div>
        {/* Timestamp */}
        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
      </div>
    </div>
  );
}
