from abc import ABC, abstractmethod
from typing import List, Dict, Any

class LLMProvider(ABC):
    """
    Abstract base class for Large Language Model providers.
    """

    @abstractmethod
    def analyze_sentiment(self, text: str) -> float:
        """
        Analyzes the sentiment of a given text.

        :param text: The text to analyze.
        :return: A sentiment score from -1.0 (very negative) to 1.0 (very positive).
        """
        pass

    @abstractmethod
    def extract_themes(self, texts: List[str]) -> List[str]:
        """
        Extracts common themes from a list of texts.

        :param texts: A list of texts.
        :return: A list of identified themes.
        """
        pass

    @abstractmethod
    def generate_insight(self, data: Dict[str, Any]) -> str:
        """
        Generates a commentary or insight based on provided data.

        :param data: A dictionary of data (e.g., sentiment scores, themes).
        :return: A string containing the generated insight.
        """
        raise NotImplementedError

    @abstractmethod
    def score_relevance(self, text: str) -> float:
        """
        Scores the relevance of a given text.

        :param text: The text to score.
        :return: A relevance score.
        """
        raise NotImplementedError

    @abstractmethod
    def extract_entities_batch(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts entities from a batch of articles.

        :param articles: List of article dicts with 'id', 'title', and 'text' keys.
        :return: Dict with 'results' (list of entity extractions per article) and 'usage' (token counts).
        """
        raise NotImplementedError
