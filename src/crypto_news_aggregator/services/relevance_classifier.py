"""
Relevance classifier for articles.

Classifies articles into relevance tiers:
- Tier 1: High signal - market-moving news, regulatory changes, security incidents
- Tier 2: Medium signal - standard crypto news worth tracking
- Tier 3: Low signal - speculation, price predictions, unrelated content

Used to filter noise from signals and narratives.
"""

import re
from typing import Optional
from loguru import logger


class RelevanceClassifier:
    """
    Rule-based classifier for article relevance.

    Design principles:
    - No source authority weighting (avoid bias toward specific sources)
    - Pattern-based detection for obvious low-signal content
    - Keyword-based detection for high-signal content
    - Default to Tier 2 (include) when uncertain
    """

    # Tier 3: Low signal - exclude from signals/narratives

    # Non-crypto topics that sometimes appear in crypto RSS feeds
    NON_CRYPTO_PATTERNS = [
        # Gaming content (Decrypt covers both crypto and gaming)
        r'\bgames?\s+releasing\b',
        r'\bgames?\s+of\s+\d{4}\b',
        r'\bmost\s+anticipated\s+games\b',
        r'\bnintendo\s+switch\b',
        r'\bplaystation\b',
        r'\bxbox\b',
        r'\bsteam\s+deck\b',
        # Pure stock articles without crypto context
        r'^(?!.*\b(bitcoin|btc|crypto|blockchain|token|coin|mining)\b).*\b(aapl|googl|tsla|nvda)\b',
        r'\bstock\s+prediction\b(?!.*\b(bitcoin|btc|crypto|mining)\b)',
        r'\bearnings\s+miss\b(?!.*\b(bitcoin|btc|crypto|mining|coinbase)\b)',
        # Stock trading without crypto context
        r'^(?!.*\b(bitcoin|btc|crypto|blockchain)\b).*\bsold\s+(nvda|tsla|aapl|googl)\b',
    ]

    # Speculation and "crystal ball" content
    SPECULATION_PATTERNS = [
        r'\bcrystal\s+ball\b',
        r'\bwill\s+\w+\s+finally\b',
        r'\bcould\s+.{0,40}(launch|spark|trigger|send|push)\b.*\brally\b',  # Allow words between
        r'\bis\s+it\s+entering\s+a\s+recovery\b',
        r'\bunstoppable\?\s*$',
        r'\bgo(ing)?\s+parabolic\b',
        r'\bto\s+the\s+moon\b',
        r'\bwhat\'?s?\s+a\s+\$?\d+\s+investment\b',
        r'\bhow\s+many\s+coins?\s+need\s+to\s+be\s+burned\b',
        r'\bai\s+chatbots?\s+(offer|predict|say)\b',
        r'\bcould\s+.{0,30}\d+%\s+rally\b',  # "Could X Launch 50% Rally"
    ]

    # Price prediction articles (routine, low signal)
    PRICE_PREDICTION_PATTERNS = [
        r'^price\s+predictions?\s+\d+/\d+',  # "Price predictions 1/2: BTC, ETH..."
        r'\bprice\s+prediction\s+\d{4}\b',
        r'\b(btc|eth|xrp|sol|doge)\s+to\s+hit\s+\$[\d,]+\b',
        r'\bcould\s+reach\s+\$[\d,]+\b',
        r'\btarget\s+of\s+\$[\d,]+\b',
        r'\bprice\s+levels?\s+to\s+watch\b',
    ]

    # Retrospective/listicle content (low immediate value)
    RETROSPECTIVE_PATTERNS = [
        r'\bwtf\s+moments?\s+of\s+(the\s+)?year\b',
        r'\bstories\s+that\s+shook\b',
        r'\bbest\s+of\s+\d{4}\b',
        r'\btop\s+\d+\s+moments?\s+of\b',
        r'\byear\s+in\s+review\b',
    ]

    # Tier 1: High signal - prioritize in signals/narratives

    # Regulatory and legal (market-moving)
    REGULATORY_KEYWORDS = [
        r'\bsec\b',
        r'\bcftc\b',
        r'\bdoj\b',
        r'\bfbi\b',
        r'\bcommissioner\b',
        r'\bregulat(or|ory|ion)\b',
        r'\blegaliz(e|es|ed|ation)\b',
        r'\bban(s|ned|ning)?\b.*\bcrypto\b',
        r'\bcrypto\b.*\bban(s|ned|ning)?\b',
        r'\blegislat(ion|ive)\b',
        r'\bbill\s+(pass|propos|approv)\b',
        r'\bexecutive\s+order\b',
        r'\btax\s+(framework|ruling|guidance)\b',
    ]

    # Security incidents (urgent, market-moving)
    SECURITY_KEYWORDS = [
        r'\bhack(ed|ing|s)?\b',  # Note: "hacker" alone can be historical - handled separately
        r'\bexploit(ed|s)?\b',
        r'\bdrain(ed|ing|s)?\b',
        r'\bstolen\b',
        r'\bbreach(ed|es)?\b',
        r'\bvulnerability\b',
        r'\battack(ed|er|s)?\b',
        r'\brug\s*pull\b',
        r'\bscam\b.*\b(million|billion)\b',
    ]

    # Patterns that indicate historical/follow-up security stories (not market-moving)
    HISTORICAL_SECURITY_PATTERNS = [
        r'\bhacker\b.{0,30}\b(released|sentenced|arrested|prison|jail|plea|guilty|charged)\b',
        r'\b(released|sentenced|arrested)\b.{0,30}\bhacker\b',
        r'\bhack(er)?\b.{0,20}\bcredits?\b',  # "hacker credits X for early release"
    ]

    # Hard market data (factual, actionable)
    MARKET_DATA_KEYWORDS = [
        r'\bliquidat(ed|ion|ions)\b.*\$\d+',
        r'\$\d+\s*(million|billion|m|b)\s+(in\s+)?(liquidat|outflow|inflow)',
        r'\betf\s+(in|out)flow',
        r'\b(in|out)flow(s)?\b.*\betf\b',
        r'\betf[s]?\s+(lose|lost|gain)\b.*\b(billion|million)\b',  # ETF loses $X billion
        r'\b(billion|million)\b.*\betf\b',  # $X billion in ETF
        r'\ball[- ]time\s+high\b',
        r'\bath\b',
        r'\brecord\s+(high|low|volume|outflow|inflow)\b',
        r'\bmarket\s+cap\b.*\b(trillion|billion)\b',
        # Large capital movements
        r'\$\d+\s*(billion|trillion)\b.{0,30}\b(left|exit|fled|flow|move)\b',
        r'\b(billion|trillion)\b.{0,20}\b(left|exit|fled)\b',
    ]

    # Major institutional/corporate moves
    INSTITUTIONAL_KEYWORDS = [
        r'\b(bought|buys?|purchase[ds]?|acquir)\b.*\b(bitcoin|btc|eth)\b',
        r'\b(bitcoin|btc|eth)\b.*\b(bought|buys?|purchase[ds]?|acquir)\b',
        r'\bipo\b',
        r'\bacquisition\b',
        r'\bpartnership\b.*\b(announc|sign|form)\b',
        r'\b(blackrock|fidelity|vanguard|jpmorgan|goldman)\b',
        r'\btreasury\b.*\b(bitcoin|btc|strategy)\b',
    ]

    # Country-level adoption
    ADOPTION_KEYWORDS = [
        r'\b(country|nation|government)\b.*\b(adopt|accept|legalize)\b',
        r'\b(adopt|accept|legalize)\b.*\b(country|nation|government)\b',
        r'\blegal\s+tender\b',
        r'\bcentral\s+bank\s+digital\b',
        r'\bcbdc\b',
        r'\bde-?dollarization\b',
    ]

    def __init__(self):
        # Pre-compile patterns for performance
        self._tier3_patterns = self._compile_patterns([
            *self.NON_CRYPTO_PATTERNS,
            *self.SPECULATION_PATTERNS,
            *self.PRICE_PREDICTION_PATTERNS,
            *self.RETROSPECTIVE_PATTERNS,
        ])

        self._tier1_patterns = self._compile_patterns([
            *self.REGULATORY_KEYWORDS,
            *self.SECURITY_KEYWORDS,
            *self.MARKET_DATA_KEYWORDS,
            *self.INSTITUTIONAL_KEYWORDS,
            *self.ADOPTION_KEYWORDS,
        ])

        # Patterns that demote from Tier 1 to Tier 2 (historical/follow-up stories)
        self._tier1_exceptions = self._compile_patterns(self.HISTORICAL_SECURITY_PATTERNS)

    def _compile_patterns(self, patterns: list[str]) -> list[re.Pattern]:
        """Compile regex patterns with case-insensitive flag."""
        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
        return compiled

    def _matches_any(self, text: str, patterns: list[re.Pattern]) -> tuple[bool, Optional[str]]:
        """Check if text matches any pattern, return match details."""
        for pattern in patterns:
            if pattern.search(text):
                return True, pattern.pattern
        return False, None

    def classify(
        self,
        title: str,
        text: Optional[str] = None,
        source: Optional[str] = None,
    ) -> dict:
        """
        Classify an article's relevance tier.

        Args:
            title: Article title (primary signal)
            text: Article body text (secondary signal, optional)
            source: Article source (for debugging, not used in scoring)

        Returns:
            dict with:
                - tier: int (1, 2, or 3)
                - reason: str explaining classification
                - matched_pattern: str or None
        """
        # Combine title and text for matching, but weight title heavily
        title_lower = title.lower()
        combined = f"{title} {text[:500] if text else ''}".lower()

        # Check Tier 3 patterns first (exclude)
        # Title-only check for most patterns (more reliable)
        is_tier3, pattern = self._matches_any(title_lower, self._tier3_patterns)
        if is_tier3:
            return {
                "tier": 3,
                "reason": "low_signal",
                "matched_pattern": pattern,
            }

        # Check Tier 1 patterns (high signal)
        is_tier1_title, pattern = self._matches_any(title_lower, self._tier1_patterns)
        if is_tier1_title:
            # Check for exceptions (historical stories that shouldn't be Tier 1)
            is_exception, _ = self._matches_any(title_lower, self._tier1_exceptions)
            if is_exception:
                return {
                    "tier": 2,
                    "reason": "historical_security",
                    "matched_pattern": pattern,
                }
            return {
                "tier": 1,
                "reason": "high_signal_title",
                "matched_pattern": pattern,
            }

        # Check body text for Tier 1 patterns (weaker signal)
        if text:
            # Only check first portion of text to avoid false positives
            text_preview = text[:1000].lower()
            is_tier1_body, pattern = self._matches_any(text_preview, self._tier1_patterns)
            if is_tier1_body:
                return {
                    "tier": 1,
                    "reason": "high_signal_body",
                    "matched_pattern": pattern,
                }

        # Default to Tier 2 (standard crypto news)
        return {
            "tier": 2,
            "reason": "default",
            "matched_pattern": None,
        }

    def classify_batch(self, articles: list[dict]) -> list[dict]:
        """
        Classify multiple articles.

        Args:
            articles: List of dicts with 'title', optional 'text', optional 'source'

        Returns:
            List of classification results with article index
        """
        results = []
        for i, article in enumerate(articles):
            result = self.classify(
                title=article.get("title", ""),
                text=article.get("text"),
                source=article.get("source"),
            )
            result["index"] = i
            results.append(result)
        return results


# Module-level instance for convenience
_classifier: Optional[RelevanceClassifier] = None


def get_classifier() -> RelevanceClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = RelevanceClassifier()
    return _classifier


def classify_article(
    title: str,
    text: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """
    Convenience function to classify a single article.

    Returns:
        dict with tier (1-3), reason, and matched_pattern
    """
    return get_classifier().classify(title, text, source)
