"""
Template rendering utility for email notifications.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..core.config import get_settings
from .template_filters import template_filters

class TemplateRenderer:
    """Handles rendering of email templates."""
    
    def __init__(self):
        # Set up the template environment
        template_path = Path(__file__).parent.parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(template_path),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['format_currency'] = self._format_currency
        self.env.filters.update(template_filters)
        
        # Add custom globals
        self.env.globals['now'] = datetime.utcnow
        
        # Add global template variables
        settings = get_settings()
        self.globals = {
            'app_name': 'Crypto News Aggregator',
            'base_url': settings.BASE_URL,
            'current_year': 2025  # This will be updated with actual year at runtime
        }
    
    async def render_template(
        self, 
        template_name: str, 
        context: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of the template file (relative to templates directory)
            context: Dictionary of variables to pass to the template
            **kwargs: Additional variables to pass to the template
            
        Returns:
            Rendered template as a string
        """
        if context is None:
            context = {}
            
        # Update context with global variables and any additional kwargs
        context.update(self.globals)
        context.update(kwargs)
        
        # Update current year
        from datetime import datetime
        context['current_year'] = datetime.now().year
        
        # Add settings to context
        context['settings'] = get_settings()
        
        # Render the template
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    @staticmethod
    def _format_currency(value: float, currency: str = 'USD') -> str:
        """
        Format a number as currency.
        
        Args:
            value: The numeric value to format
            currency: The currency code (default: 'USD')
            
        Returns:
            Formatted currency string (e.g., "1,234.56 USD")
        """
        try:
            return f"{float(value):,.2f} {currency}"
        except (ValueError, TypeError):
            return str(value)
            
    @staticmethod
    def format_datetime(value: Any, format_str: str = '%b %d, %Y %H:%M') -> str:
        """
        Format a datetime object or ISO format string.
        
        Args:
            value: Datetime object or ISO format string
            format_str: Format string (default: '%b %d, %Y %H:%M')
            
        Returns:
            Formatted date string or empty string if invalid
        """
        return template_filters['datetimeformat'](value, format_str)

# Create a singleton instance
template_renderer = TemplateRenderer()
