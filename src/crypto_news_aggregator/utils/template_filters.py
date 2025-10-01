"""
Custom template filters for Jinja2 templates.
"""

from datetime import datetime
from typing import Any, Optional


def datetimeformat(value: Optional[Any], format: str = "%b %d, %Y %H:%M") -> str:
    """
    Format a datetime object or ISO format string.

    Args:
        value: Datetime object or ISO format string
        format: Format string (default: '%b %d, %Y %H:%M')

    Returns:
        Formatted date string or empty string if invalid
    """
    if not value:
        return ""

    # If it's already a datetime object
    if isinstance(value, datetime):
        return value.strftime(format)

    # If it's a string in ISO format
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime(format)
    except (ValueError, TypeError):
        return str(value) if value else ""


# Dictionary of filters to register with Jinja2
template_filters = {
    "datetimeformat": datetimeformat,
}
