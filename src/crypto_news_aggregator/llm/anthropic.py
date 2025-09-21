import os
import json
from typing import List, Dict, Any
import httpx
from .base import LLMProvider
from .tracking import track_usage

class AnthropicProvider(LLMProvider):
    """
    LLM provider for Anthropic's Claude models, using direct httpx calls to bypass client issues.
    """
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str = None, model_name: str = "claude-3-haiku-20240307"): # Reverted to Haiku as Sonnet is unavailable.
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided or found in environment variables.")
        self.model_name = model_name

    def _get_completion(self, prompt: str) -> str:
        headers = {
            "x-api-key": self.api_key,
                                    "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            with httpx.Client() as client:
                response = client.post(self.API_URL, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                data = response.json()
                return data.get("content", [{}])[0].get("text", "")
        except httpx.HTTPStatusError as e:
            print(f"Anthropic API request failed with status {e.response.status_code}: {e.response.text}")
            return ""
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return ""

    @track_usage
    def analyze_sentiment(self, text: str) -> float:
        prompt = f"Analyze the sentiment of this crypto text. Return only a number from -1.0 (very bearish) to 1.0 (very bullish):\n\n{text}"
        response = self._get_completion(prompt)
        try:
            return float(response.strip())
        except (ValueError, TypeError):
            return 0.0

    @track_usage
    def extract_themes(self, texts: List[str]) -> List[str]:
        combined_texts = "\n".join(texts)
        prompt = f"Extract the key crypto themes from the following texts. Respond with ONLY a comma-separated list of keywords (e.g., 'Bitcoin, DeFi, Regulation'). Do not include any preamble.\n\nTexts:\n{combined_texts}"
        response = self._get_completion(prompt)
        if response:
            return [theme.strip() for theme in response.split(',')]
        return []

    @track_usage
    def generate_insight(self, data: Dict[str, Any]) -> str:
        sentiment_score = data.get("sentiment_score", 0.0)
        themes = data.get("themes", [])
        prompt = f"Given a sentiment score of {sentiment_score} and the themes {', '.join(themes)}, generate a concise market insight for cryptocurrency traders. The response must be a maximum of 2-3 sentences."
        return self._get_completion(prompt)
