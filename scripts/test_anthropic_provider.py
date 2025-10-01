import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.crypto_news_aggregator.llm.anthropic import AnthropicProvider


def run_test():
    """
    Tests the AnthropicProvider implementation.
    """
    try:
        provider = AnthropicProvider()
    except ValueError as e:
        print(f"Error: {e}")
        print(
            "Please make sure your ANTHROPIC_API_KEY is set in your environment variables."
        )
        return

    print(f"Using model: {provider.model_name}")

    # Test sentiment analysis
    print("\n--- Testing Sentiment Analysis ---")
    sample_text = "Bitcoin is surging after the new ETF announcement. This is a very bullish sign for the entire crypto market."
    print(f"Analyzing text: '{sample_text}'")
    sentiment = provider.analyze_sentiment(sample_text)
    print(f"Sentiment score: {sentiment}")

    # Test theme extraction
    print("\n--- Testing Theme Extraction ---")
    sample_texts = [
        "Ethereum's upcoming Dencun upgrade is expected to lower gas fees significantly.",
        "Solana's ecosystem is growing, with many new DeFi projects launching.",
        "The SEC is cracking down on unregistered crypto securities.",
    ]
    print(f"Extracting themes from texts:")
    for text in sample_texts:
        print(f"- {text}")
    themes = provider.extract_themes(sample_texts)
    print(f"Extracted themes: {themes}")

    # Test insight generation
    print("\n--- Testing Insight Generation ---")
    insight_data = {"sentiment_score": sentiment, "themes": themes}
    print(f"Generating insight with sentiment {sentiment} and themes {themes}")
    insight = provider.generate_insight(insight_data)
    print(f"Generated insight: {insight}")


if __name__ == "__main__":
    run_test()
