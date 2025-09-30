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

    def __init__(self, api_key: str, model_name: str = "claude-3-haiku-20240307"): # Reverted to Haiku as Sonnet is unavailable.
        if not api_key:
            raise ValueError("Anthropic API key not provided.")
        self.api_key = api_key
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
        prompt = f"Analyze the sentiment of this crypto text. Return ONLY a single number from -1.0 (very bearish) to 1.0 (very bullish). Do not include any explanation or additional text. Just the number:\n\n{text}"
        response = self._get_completion(prompt)
        try:
            # Extract the first number from the response (in case there's extra text)
            import re
            numbers = re.findall(r'[-+]?\d*\.\d+|\d+', response.strip())
            if numbers:
                return float(numbers[0])
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

    @track_usage
    def score_relevance(self, text: str) -> float:
        prompt = f"On a scale from 0.0 to 1.0, how relevant is this text to cryptocurrency market movements? Return ONLY a single floating-point number with no explanation:\n\n{text}"
        response = self._get_completion(prompt)
        try:
            # Extract the first number from the response (in case there's extra text)
            import re
            numbers = re.findall(r'[-+]?\d*\.\d+|\d+', response.strip())
            if numbers:
                return float(numbers[0])
            return float(response.strip())
        except (ValueError, TypeError):
            return 0.0

    def extract_entities_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts entities from a batch of articles using Claude Haiku.
        Returns structured data with entities for each article and usage metrics.
        """
        from ..core.config import settings
        
        # Build the batch prompt
        articles_text = []
        for idx, article in enumerate(articles):
            article_id = article.get('id', f'article_{idx}')
            title = article.get('title', '')
            text = article.get('text', '')
            articles_text.append(f"Article {idx} (ID: {article_id}):\nTitle: {title}\nText: {text}\n")
        
        combined_articles = "\n---\n".join(articles_text)
        
        prompt = f"""Analyze the following {len(articles)} cryptocurrency news articles and extract entities from each.

For each article, identify:
1. Ticker symbols (e.g., $BTC, $ETH, $SOL) - include the $ prefix
2. Project names (e.g., Bitcoin, Ethereum, Solana, Aster Protocol)
3. Event types (choose from: launch, hack, partnership, regulation, upgrade, acquisition, listing, delisting, airdrop, other)
4. Sentiment (positive, negative, or neutral)

Return ONLY a valid JSON array with one object per article, in the same order as provided. Each object must have this exact structure:
{{
  "article_index": 0,
  "article_id": "the_id_from_input",
  "entities": [
    {{"type": "ticker", "value": "$BTC", "confidence": 0.95}},
    {{"type": "project", "value": "Bitcoin", "confidence": 0.95}},
    {{"type": "event", "value": "regulation", "confidence": 0.85}}
  ],
  "sentiment": "positive"
}}

Articles:
{combined_articles}

Return ONLY the JSON array, no other text."""

        # Use entity extraction model from config
        entity_model = settings.ANTHROPIC_ENTITY_MODEL
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": entity_model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        
        try:
            with httpx.Client() as client:
                response = client.post(self.API_URL, headers=headers, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                
                # Extract response text
                response_text = data.get("content", [{}])[0].get("text", "")
                
                # Extract usage metrics
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                
                # Calculate costs
                input_cost = (input_tokens / 1000) * settings.ANTHROPIC_ENTITY_INPUT_COST_PER_1K_TOKENS
                output_cost = (output_tokens / 1000) * settings.ANTHROPIC_ENTITY_OUTPUT_COST_PER_1K_TOKENS
                total_cost = input_cost + output_cost
                
                # Parse JSON response
                import re
                # Try to extract JSON array from response
                json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
                if json_match:
                    results = json.loads(json_match.group(0))
                else:
                    results = json.loads(response_text)
                
                return {
                    "results": results,
                    "usage": {
                        "model": entity_model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost,
                    }
                }
        except httpx.HTTPStatusError as e:
            print(f"Anthropic API request failed with status {e.response.status_code}: {e.response.text}")
            return {"results": [], "usage": {}}
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {e}")
            return {"results": [], "usage": {}}
        except Exception as e:
            print(f"Entity extraction failed: {e}")
            return {"results": [], "usage": {}}
