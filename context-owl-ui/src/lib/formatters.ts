/**
 * Format a date string to a human-readable format
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/**
 * Format a relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return 'just now';
  }

  const diffInMinutes = Math.floor(diffInSeconds / 60);
  if (diffInMinutes < 60) {
    return `${diffInMinutes} minute${diffInMinutes > 1 ? 's' : ''} ago`;
  }

  const diffInHours = Math.floor(diffInMinutes / 60);
  if (diffInHours < 24) {
    return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
  }

  const diffInDays = Math.floor(diffInHours / 24);
  if (diffInDays < 7) {
    return `${diffInDays} day${diffInDays > 1 ? 's' : ''} ago`;
  }

  return formatDate(dateString);
}

/**
 * Format a number with commas
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Format a percentage
 */
export function formatPercentage(num: number, decimals: number = 1): string {
  return `${(num * 100).toFixed(decimals)}%`;
}

/**
 * Format sentiment score to a readable label
 */
export function formatSentiment(score: number | null): string {
  if (score === null) return 'Neutral';
  if (score > 0.3) return 'Positive';
  if (score < -0.3) return 'Negative';
  return 'Neutral';
}

/**
 * Get color class for sentiment
 */
export function getSentimentColor(score: number | null): string {
  if (score === null) return 'text-gray-500';
  if (score > 0.3) return 'text-green-600';
  if (score < -0.3) return 'text-red-600';
  return 'text-gray-500';
}

/**
 * Get color class for signal strength
 */
export function getSignalStrengthColor(strength: number): string {
  if (strength >= 0.7) return 'text-red-600';
  if (strength >= 0.4) return 'text-yellow-600';
  return 'text-blue-600';
}

/**
 * Truncate text to a maximum length
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}
