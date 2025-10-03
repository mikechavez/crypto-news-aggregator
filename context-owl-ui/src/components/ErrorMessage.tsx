interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
        <h3 className="text-red-800 font-semibold mb-2">Error</h3>
        <p className="text-red-700 mb-4">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
