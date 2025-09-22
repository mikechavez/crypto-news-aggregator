from typing import List, Optional

from .base import LLMProvider
from .sentient import SentientProvider
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider
from ..core.config import get_settings

PROVIDER_MAP = {
    "sentient": SentientProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}

def get_llm_provider() -> LLMProvider:
    """
    Factory function to get an LLM provider instance.

    :param provider_name: The name of the provider to use. If not provided, it will be read from the LLM_PROVIDER environment variable.
    :param fallback_chain: A list of provider names to use as fallbacks.
    :return: An instance of the LLM provider.
    """
    settings = get_settings()
    provider_name = getattr(settings, 'LLM_PROVIDER', 'openai').lower()
    providers_to_try = [provider_name]

    last_exception = None
    for name in providers_to_try:
        provider_class = PROVIDER_MAP.get(name)
        if provider_class:
            try:
                api_key = None
                if name == "anthropic":
                    api_key = settings.ANTHROPIC_API_KEY
                elif name == "openai":
                    api_key = settings.OPENAI_API_KEY
                
                return provider_class(api_key=api_key)
            except Exception as e:
                last_exception = e
                print(f"Failed to initialize provider '{name}': {e}")
                continue
    
    raise RuntimeError(
        f"Could not initialize any of the specified LLM providers: {providers_to_try}. "
        f"Last error: {last_exception}"
    )
