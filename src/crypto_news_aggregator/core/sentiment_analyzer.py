import logging
from typing import Dict, Optional, Tuple
from textblob import TextBlob

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """
    A simple sentiment analyzer using TextBlob.
    Provides polarity and subjectivity scores for text.
    """
    
    @staticmethod
    def analyze_text(text: str) -> Dict[str, float]:
        """
        Analyze the sentiment of the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dict containing 'polarity' and 'subjectivity' scores
        """
        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided for sentiment analysis")
            return {"polarity": 0.0, "subjectivity": 0.0}
            
        try:
            blob = TextBlob(text)
            sentiment = blob.sentiment
            
            return {
                "polarity": float(sentiment.polarity),  # Range: -1.0 to 1.0
                "subjectivity": float(sentiment.subjectivity)  # Range: 0.0 to 1.0
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {"polarity": 0.0, "subjectivity": 0.0}
    
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
    def analyze_article(cls, article_text: str, title: Optional[str] = None) -> Dict[str, any]:
        """
        Analyze sentiment of an article, optionally including its title.
        
        Args:
            article_text: The main text of the article
            title: Optional article title (will be included in analysis if provided)
            
        Returns:
            Dict containing sentiment analysis results
        """
        # Combine title and text if title is provided
        text_to_analyze = f"{title}. {article_text}" if title else article_text
        
        # Get sentiment scores
        sentiment = cls.analyze_text(text_to_analyze)
        
        # Get sentiment label
        sentiment["label"] = cls.get_sentiment_label(sentiment["polarity"])
        
        return sentiment
