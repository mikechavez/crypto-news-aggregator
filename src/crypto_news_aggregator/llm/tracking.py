import functools
from collections import Counter

# A simple in-memory store for usage tracking.
# In a real application, you might want to use a more persistent store.
USAGE_COUNTER = Counter()

def track_usage(func):
    """
    A decorator to track the usage of LLM provider methods.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        provider_name = self.__class__.__name__
        method_name = func.__name__
        USAGE_COUNTER[f"{provider_name}.{method_name}"] += 1
        return func(self, *args, **kwargs)
    return wrapper

def get_usage_stats():
    """
    Returns the current usage statistics.
    """
    return dict(USAGE_COUNTER)

def reset_usage_stats():
    """
    Resets the usage statistics.
    """
    USAGE_COUNTER.clear()
