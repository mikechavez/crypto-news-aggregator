import logging
from typing import Dict, Optional, Tuple, Union, Any
from textblob import TextBlob

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    A simple sentiment analyzer using TextBlob.
    Provides polarity and subjectivity scores for text.
    """

    @classmethod
    def analyze_text(cls, text: str) -> Dict[str, Union[float, str]]:
        """
        Analyze the sentiment of the given text.

        Args:
            text: The text to analyze

        Returns:
            Dict containing 'polarity', 'subjectivity', and 'label' scores
        """
        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided for sentiment analysis")
            return {"polarity": 0.0, "subjectivity": 0.0, "label": "Neutral"}

        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment
            polarity = float(sentiment.polarity)

            return {
                "polarity": polarity,  # Range: -1.0 to 1.0
                "subjectivity": float(sentiment.subjectivity),  # Range: 0.0 to 1.0
                "label": cls.get_sentiment_label(polarity),  # Positive/Neutral/Negative
            }

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {"polarity": 0.0, "subjectivity": 0.0, "label": "Neutral"}

    @classmethod
    def get_sentiment_label(cls, polarity: float) -> str:
        """
        Convert polarity score to a human-readable label.

        Args:
            polarity: Polarity score from -1.0 to 1.0

        Returns:
            str: Sentiment label ("Negative", "Neutral", or "Positive")
        """
        if polarity > 0.1:
            return "Positive"
        elif polarity < -0.1:
            return "Negative"
        return "Neutral"

    @classmethod
    def analyze_article(
        cls, content: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze the sentiment of an article with optional title.

        Args:
            content: The main content of the article
            title: Optional title of the article

        Returns:
            Dict containing 'polarity', 'subjectivity', and 'label' scores
        """
        if not content and not title:
            return {"polarity": 0.0, "subjectivity": 0.0, "label": "Neutral"}

        # Combine title and content for analysis if title is provided
        text_to_analyze = f"{title}. {content}" if title else content
        return cls.analyze_text(text_to_analyze)
