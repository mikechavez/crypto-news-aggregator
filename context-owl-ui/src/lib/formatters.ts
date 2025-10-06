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

/**
 * Format entity type for display
 * Maps technical entity types to user-friendly labels
 */
export function formatEntityType(entityType: string): string {
  const typeMap: Record<string, string> = {
    'cryptocurrency': 'Cryptocurrency',
    'blockchain': 'Blockchain',
    'protocol': 'Protocol',
    'company': 'Company',
    'organization': 'Organization',
    'event': 'Event',
    'concept': 'Concept',
    'person': 'Person',
    'location': 'Location',
    'ticker': 'Ticker',
    'project': 'Project',
  };

  return typeMap[entityType.toLowerCase()] || entityType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get color class for entity type
 */
export function getEntityTypeColor(entityType: string): string {
  const colorMap: Record<string, string> = {
    'cryptocurrency': 'text-blue-600 bg-blue-50',
    'blockchain': 'text-purple-600 bg-purple-50',
    'protocol': 'text-indigo-600 bg-indigo-50',
    'company': 'text-green-600 bg-green-50',
    'organization': 'text-orange-600 bg-orange-50',
    'event': 'text-red-600 bg-red-50',
    'concept': 'text-gray-600 bg-gray-50',
    'person': 'text-pink-600 bg-pink-50',
    'location': 'text-teal-600 bg-teal-50',
    'ticker': 'text-blue-600 bg-blue-50',
    'project': 'text-indigo-600 bg-indigo-50',
  };

  return colorMap[entityType.toLowerCase()] || 'text-gray-600 bg-gray-50';
}
