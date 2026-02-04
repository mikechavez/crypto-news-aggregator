import { AlertTriangle } from 'lucide-react';

interface CostAlertProps {
  dailyCost: number;
  projectedMonthly: number;
  target?: number;
}

export function CostAlert({ dailyCost, projectedMonthly, target = 10 }: CostAlertProps) {
  const DAILY_THRESHOLD = 0.50;

  const showDailyAlert = dailyCost > DAILY_THRESHOLD;
  const showMonthlyAlert = projectedMonthly > target;

  if (!showDailyAlert && !showMonthlyAlert) return null;

  return (
    <div className="bg-red-50 dark:bg-red-900/20 border-l-4 border-red-500 p-4 mb-6 rounded-lg">
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-6 w-6 text-red-500 mt-0.5 shrink-0" />
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
            Cost Alert
          </h3>
          <ul className="list-disc list-inside space-y-1 text-red-700 dark:text-red-300 text-sm">
            {showDailyAlert && (
              <li>
                Daily cost (${dailyCost.toFixed(2)}) exceeds ${DAILY_THRESHOLD.toFixed(2)} threshold
              </li>
            )}
            {showMonthlyAlert && (
              <li>
                Projected monthly (${projectedMonthly.toFixed(2)}) exceeds ${target.toFixed(2)} budget
              </li>
            )}
          </ul>
          <div className="mt-3 text-sm text-red-600 dark:text-red-400">
            <strong>Recommended actions:</strong>
            <ul className="list-disc list-inside mt-1 ml-4">
              <li>Review cache hit rate (target: &gt;85%)</li>
              <li>Check for unexpected high-volume operations</li>
              <li>Consider reducing briefing frequency</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
