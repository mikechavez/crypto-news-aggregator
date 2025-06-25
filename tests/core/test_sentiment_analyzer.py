import pytest
from crypto_news_aggregator.core.sentiment_analyzer import SentimentAnalyzer

def test_analyze_text_positive():
    """Test sentiment analysis with positive text."""
    text = "I love this amazing product! It works perfectly and I'm very happy with it."
    result = SentimentAnalyzer.analyze_text(text)
    
    assert isinstance(result, dict)
    assert "polarity" in result
    assert "subjectivity" in result
    assert result["polarity"] > 0.5  # Should be quite positive
    assert 0.5 <= result["subjectivity"] <= 1.0  # Subjective text

def test_analyze_text_negative():
    """Test sentiment analysis with negative text."""
    text = "This is terrible. I hate how slow and buggy this software is. Worst experience ever."
    result = SentimentAnalyzer.analyze_text(text)
    
    assert result["polarity"] < -0.3  # Should be quite negative

def test_analyze_text_neutral():
    """Test sentiment analysis with neutral text."""
    text = "This is a neutral statement. It contains no strong opinions or emotions."
    result = SentimentAnalyzer.analyze_text(text)
    
    assert -0.1 <= result["polarity"] <= 0.1  # Should be close to neutral

def test_get_sentiment_label():
    """Test sentiment label classification."""
    assert SentimentAnalyzer.get_sentiment_label(0.8) == "Positive"
    assert SentimentAnalyzer.get_sentiment_label(-0.3) == "Negative"
    assert SentimentAnalyzer.get_sentiment_label(0.05) == "Neutral"
    assert SentimentAnalyzer.get_sentiment_label(-0.05) == "Neutral"

def test_analyze_article():
    """Test analyzing a full article with title."""
    title = "Amazing new cryptocurrency reaches all-time high!"
    content = "Investors are thrilled with the recent performance of this new digital asset. The market response has been overwhelmingly positive."
    
    result = SentimentAnalyzer.analyze_article(content, title)
    
    assert "polarity" in result
    assert "subjectivity" in result
    assert "label" in result
    assert result["polarity"] > 0.3  # Should be positive
    assert result["label"] == "Positive"

def test_empty_text():
    """Test with empty or invalid text input."""
    result = SentimentAnalyzer.analyze_text("")
    assert result["polarity"] == 0.0
    assert result["subjectivity"] == 0.0
    
    result = SentimentAnalyzer.analyze_text(None)  # type: ignore
    assert result["polarity"] == 0.0
    assert result["subjectivity"] == 0.0
