/**
 * Safely parse a date string, returning a valid Date or current date as fallback
 */
function parseDate(dateString: string | null | undefined): Date {
  if (!dateString) return new Date();
  const date = new Date(dateString);
  return isNaN(date.getTime()) ? new Date() : date;
}

/**
 * Format a date string to a human-readable format
 */
export function formatDate(dateString: string): string {
  const date = parseDate(dateString);
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
  const date = parseDate(dateString);
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
 * Get color class for signal strength
 */
export function getSignalStrengthColor(strength: number): string {
  if (strength >= 0.7) return 'text-red-600 dark:text-red-400';
  if (strength >= 0.4) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-blue-600 dark:text-blue-400';
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
    'cryptocurrency': 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
    'blockchain': 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300',
    'protocol': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300',
    'company': 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300',
    'organization': 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300',
    'event': 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300',
    'concept': 'bg-gray-100 dark:bg-gray-700/30 text-gray-800 dark:text-gray-300',
    'person': 'bg-pink-100 dark:bg-pink-900/30 text-pink-800 dark:text-pink-300',
    'location': 'bg-teal-100 dark:bg-teal-900/30 text-teal-800 dark:text-teal-300',
    'ticker': 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300',
    'project': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-800 dark:text-indigo-300',
  };

  return colorMap[entityType.toLowerCase()] || 'bg-gray-100 dark:bg-gray-700/30 text-gray-800 dark:text-gray-300';
}

/**
 * Format theme for display
 * Maps technical theme names to user-friendly labels
 */
export function formatTheme(theme: string): string {
  const themeMap: Record<string, string> = {
    'regulatory': 'Regulatory',
    'defi_adoption': 'DeFi Adoption',
    'institutional_investment': 'Institutional',
    'technology_upgrade': 'Tech Upgrade',
    'market_volatility': 'Market Volatility',
    'security_breach': 'Security',
    'partnership': 'Partnership',
    'ecosystem_growth': 'Ecosystem',
  };

  return themeMap[theme] || theme.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Get color class for narrative theme badge
 */
export function getThemeColor(theme: string): string {
  const colorMap: Record<string, string> = {
    'regulatory': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50',
    'defi_adoption': 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50',
    'institutional_investment': 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50',
    'technology_upgrade': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50',
    'market_volatility': 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 hover:bg-orange-200 dark:hover:bg-orange-900/50',
    'security_breach': 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50',
    'partnership': 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-200 dark:hover:bg-indigo-900/50',
    'ecosystem_growth': 'bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 hover:bg-teal-200 dark:hover:bg-teal-900/50',
  };

  return colorMap[theme] || 'bg-gray-100 dark:bg-gray-700/30 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700/50';
}
