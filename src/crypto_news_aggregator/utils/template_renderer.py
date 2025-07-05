"""
Template rendering utility for email notifications.
"""
import os
from pathlib import Path
from typing import Any, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..core.config import settings

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
        
        # Add global template variables
        self.globals = {
            'app_name': 'Crypto News Aggregator',
            'base_url': settings.BASE_URL if hasattr(settings, 'BASE_URL') else 'http://localhost:8000',
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
        context['settings'] = settings
        
        # Render the template
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    @staticmethod
    def _format_currency(value: float, currency: str = 'USD') -> str:
        """Format a number as currency."""
        try:
            return f"{float(value):,.2f} {currency}"
        except (ValueError, TypeError):
            return str(value)

# Create a singleton instance
template_renderer = TemplateRenderer()
