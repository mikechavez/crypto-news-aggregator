"""
Pattern Detection Service for the Briefing Agent.

Detects patterns in market data that are useful for the briefing:
- Entity frequency changes (week-over-week surges)
- Sentiment shifts in narratives
- Expected major events (from narrative content)
- Narrative emergence patterns

These patterns help the briefing agent identify what's changing
rather than just what exists.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.services.entity_normalization import normalize_entity_name

logger = logging.getLogger(__name__)


@dataclass
class DetectedPattern:
    """A pattern detected by the pattern detector."""

    pattern_type: str  # entity_surge, sentiment_shift, event_expected, narrative_emergence
    description: str
    entities: List[str]
    confidence: float  # 0.0 - 1.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternSummary:
    """Summary of all detected patterns."""

    entity_surges: List[DetectedPattern]
    sentiment_shifts: List[DetectedPattern]
    expected_events: List[DetectedPattern]
    narrative_emergences: List[DetectedPattern]

    def all_patterns(self) -> List[DetectedPattern]:
        """Get all patterns as a flat list."""
        return (
            self.entity_surges +
            self.sentiment_shifts +
            self.expected_events +
            self.narrative_emergences
        )

    def to_prompt_context(self) -> str:
        """Format patterns for inclusion in LLM prompt."""
        lines = ["## Detected Patterns\n"]

        if self.entity_surges:
            lines.append("### Entity Surges (Week-over-Week)\n")
            for p in self.entity_surges[:5]:
                lines.append(f"- {p.description} (confidence: {p.confidence:.0%})\n")

        if self.sentiment_shifts:
            lines.append("\n### Sentiment Shifts\n")
            for p in self.sentiment_shifts[:5]:
                lines.append(f"- {p.description} (confidence: {p.confidence:.0%})\n")

        if self.expected_events:
            lines.append("\n### Expected Events\n")
            for p in self.expected_events[:5]:
                lines.append(f"- {p.description} (confidence: {p.confidence:.0%})\n")

        if self.narrative_emergences:
            lines.append("\n### Emerging Narratives\n")
            for p in self.narrative_emergences[:3]:
                lines.append(f"- {p.description} (confidence: {p.confidence:.0%})\n")

        return "".join(lines)


class PatternDetector:
    """
    Detects patterns in market data for the briefing agent.

    Uses MongoDB queries to compare current state vs historical state
    to identify meaningful changes.
    """

    # Thresholds for pattern detection
    SURGE_THRESHOLD = 2.0  # 2x increase = surge
    SIGNIFICANT_CHANGE_THRESHOLD = 0.5  # 50% change is significant
    MIN_MENTIONS_FOR_PATTERN = 3  # Need at least 3 mentions to consider

    # Keywords that suggest expected events
    EVENT_KEYWORDS = [
        "decision", "vote", "meeting", "deadline", "launch", "release",
        "announcement", "ruling", "verdict", "approval", "rejection",
        "hearing", "trial", "settlement", "merger", "acquisition",
        "halving", "upgrade", "fork", "airdrop", "unlock", "expiration"
    ]

    # Major institutions/events to watch
    MAJOR_ENTITIES = [
        "SEC", "Fed", "Federal Reserve", "FOMC", "CFTC", "DOJ",
        "BlackRock", "Fidelity", "Grayscale", "Coinbase", "Binance",
        "Bitcoin ETF", "Ethereum ETF", "Spot ETF"
    ]

    async def detect_all_patterns(
        self,
        current_signals: List[Dict[str, Any]],
        current_narratives: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> PatternSummary:
        """
        Detect all patterns from current data vs history.

        Args:
            current_signals: Current trending signals
            current_narratives: Current active narratives
            history: Historical briefings for comparison

        Returns:
            PatternSummary with all detected patterns
        """
        entity_surges = await self.detect_entity_frequency_changes(
            current_signals, history
        )
        sentiment_shifts = await self.detect_sentiment_shifts(
            current_narratives, history
        )
        expected_events = self.detect_expected_events(current_narratives)
        narrative_emergences = await self.detect_narrative_emergence(current_narratives)

        return PatternSummary(
            entity_surges=entity_surges,
            sentiment_shifts=sentiment_shifts,
            expected_events=expected_events,
            narrative_emergences=narrative_emergences,
        )

    async def detect_entity_frequency_changes(
        self,
        current_signals: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> List[DetectedPattern]:
        """
        Detect entities with significant week-over-week frequency changes.

        Args:
            current_signals: Current trending signals
            history: Historical briefings

        Returns:
            List of entity surge patterns
        """
        patterns = []

        # Build historical entity frequency from past briefings
        historical_entities: Dict[str, int] = {}
        for briefing in history:
            entities = briefing.get("content", {}).get("entities_mentioned", [])
            for entity in entities:
                historical_entities[entity] = historical_entities.get(entity, 0) + 1

        # Check current signals for surges
        for signal in current_signals:
            entity = signal.get("entity", "")
            if not entity:
                continue

            normalized = normalize_entity_name(entity)
            velocity = signal.get("velocity", 0)
            mentions = signal.get("mentions_24h", signal.get("source_count", 0))

            # Skip low-mention entities
            if mentions < self.MIN_MENTIONS_FOR_PATTERN:
                continue

            historical_count = historical_entities.get(normalized, 0)

            # High velocity signals a surge
            if velocity >= 200:  # 200%+ growth
                confidence = min(0.9, 0.5 + (velocity / 1000))
                patterns.append(DetectedPattern(
                    pattern_type="entity_surge",
                    description=f"{entity} mentions up {velocity:.0f}% vs previous period",
                    entities=[normalized],
                    confidence=confidence,
                    details={"velocity": velocity, "mentions": mentions}
                ))

            # Compare to historical frequency in briefings
            elif historical_count > 0:
                # Entity appeared in many past briefings but with low historical count
                briefing_count = sum(
                    1 for b in history
                    if normalized in b.get("content", {}).get("entities_mentioned", [])
                )
                total_briefings = len(history) if history else 1

                if briefing_count / total_briefings < 0.3 and mentions > 5:
                    patterns.append(DetectedPattern(
                        pattern_type="entity_surge",
                        description=f"{entity} emerging: {mentions} mentions (historically low presence)",
                        entities=[normalized],
                        confidence=0.6,
                        details={"mentions": mentions, "historical_rate": briefing_count / total_briefings}
                    ))

        return patterns[:10]  # Limit to top 10

    async def detect_sentiment_shifts(
        self,
        current_narratives: List[Dict[str, Any]],
        history: List[Dict[str, Any]],
    ) -> List[DetectedPattern]:
        """
        Detect significant sentiment shifts in narratives.

        Args:
            current_narratives: Current active narratives
            history: Historical briefings

        Returns:
            List of sentiment shift patterns
        """
        patterns = []

        # Build historical sentiment by theme from past briefings
        historical_patterns: Dict[str, List[str]] = {}
        for briefing in history:
            detected = briefing.get("content", {}).get("detected_patterns", [])
            for pattern in detected:
                if "sentiment" in pattern.lower():
                    # Extract theme if mentioned
                    for theme in ["regulatory", "defi", "institutional", "technology"]:
                        if theme in pattern.lower():
                            if theme not in historical_patterns:
                                historical_patterns[theme] = []
                            historical_patterns[theme].append(pattern)

        # Check current narratives for lifecycle changes that suggest sentiment shifts
        for narrative in current_narratives:
            theme = narrative.get("theme", "")
            lifecycle = narrative.get("lifecycle", "")
            momentum = narrative.get("momentum", "unknown")

            # Lifecycle transitions can indicate sentiment shifts
            if lifecycle == "cooling" and momentum == "declining":
                patterns.append(DetectedPattern(
                    pattern_type="sentiment_shift",
                    description=f"{theme.replace('_', ' ').title()} narrative cooling - momentum declining",
                    entities=narrative.get("entities", [])[:3],
                    confidence=0.7,
                    details={"theme": theme, "lifecycle": lifecycle, "momentum": momentum}
                ))
            elif lifecycle in ["rising", "hot"] and momentum == "growing":
                patterns.append(DetectedPattern(
                    pattern_type="sentiment_shift",
                    description=f"{theme.replace('_', ' ').title()} narrative gaining momentum",
                    entities=narrative.get("entities", [])[:3],
                    confidence=0.7,
                    details={"theme": theme, "lifecycle": lifecycle, "momentum": momentum}
                ))

        return patterns[:5]

    def detect_expected_events(
        self,
        current_narratives: List[Dict[str, Any]],
    ) -> List[DetectedPattern]:
        """
        Detect mentions of expected future events in narratives.

        Args:
            current_narratives: Current active narratives

        Returns:
            List of expected event patterns
        """
        patterns = []

        for narrative in current_narratives:
            title = narrative.get("title", "")
            summary = narrative.get("summary", "")
            combined_text = f"{title} {summary}".lower()

            # Check for event keywords
            for keyword in self.EVENT_KEYWORDS:
                if keyword in combined_text:
                    # Check if it mentions a major entity
                    mentioned_majors = [
                        e for e in self.MAJOR_ENTITIES
                        if e.lower() in combined_text
                    ]

                    if mentioned_majors:
                        # Extract date mentions (simple pattern)
                        date_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}'
                        date_matches = re.findall(date_pattern, combined_text)

                        description = f"{mentioned_majors[0]} {keyword} expected"
                        if date_matches:
                            description += f" ({date_matches[0]})"

                        patterns.append(DetectedPattern(
                            pattern_type="event_expected",
                            description=description,
                            entities=mentioned_majors + narrative.get("entities", [])[:2],
                            confidence=0.8 if date_matches else 0.6,
                            details={
                                "keyword": keyword,
                                "major_entity": mentioned_majors[0],
                                "theme": narrative.get("theme", "")
                            }
                        ))
                        break  # One pattern per narrative

        # Deduplicate by description
        seen = set()
        unique_patterns = []
        for p in patterns:
            if p.description not in seen:
                seen.add(p.description)
                unique_patterns.append(p)

        return unique_patterns[:5]

    async def detect_narrative_emergence(
        self,
        current_narratives: List[Dict[str, Any]],
    ) -> List[DetectedPattern]:
        """
        Detect newly emerging narratives.

        Args:
            current_narratives: Current active narratives

        Returns:
            List of narrative emergence patterns
        """
        patterns = []

        for narrative in current_narratives:
            lifecycle = narrative.get("lifecycle", "")
            first_seen = narrative.get("first_seen")

            if lifecycle in ["emerging", "rising"]:
                # Check if it's truly new (within last 48 hours)
                if first_seen:
                    if isinstance(first_seen, str):
                        first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                    elif first_seen.tzinfo is None:
                        first_seen = first_seen.replace(tzinfo=timezone.utc)

                    age_hours = (datetime.now(timezone.utc) - first_seen).total_seconds() / 3600

                    if age_hours < 48:
                        patterns.append(DetectedPattern(
                            pattern_type="narrative_emergence",
                            description=f"New narrative: {narrative.get('title', 'Untitled')}",
                            entities=narrative.get("entities", [])[:5],
                            confidence=0.8 if age_hours < 24 else 0.6,
                            details={
                                "theme": narrative.get("theme", ""),
                                "lifecycle": lifecycle,
                                "age_hours": age_hours,
                                "article_count": narrative.get("article_count", 0)
                            }
                        ))

        return patterns[:3]

    def summarize_patterns(self, patterns: PatternSummary) -> str:
        """
        Create a human-readable summary of detected patterns.

        Args:
            patterns: PatternSummary with all patterns

        Returns:
            Formatted string summary
        """
        all_patterns = patterns.all_patterns()
        if not all_patterns:
            return "No significant patterns detected."

        summary_parts = []

        if patterns.entity_surges:
            surge_names = [p.entities[0] for p in patterns.entity_surges[:3] if p.entities]
            summary_parts.append(f"Entity surges: {', '.join(surge_names)}")

        if patterns.expected_events:
            event_descs = [p.description for p in patterns.expected_events[:2]]
            summary_parts.append(f"Expected events: {'; '.join(event_descs)}")

        if patterns.narrative_emergences:
            new_narrs = [p.details.get("theme", "unknown") for p in patterns.narrative_emergences[:2]]
            summary_parts.append(f"Emerging narratives: {', '.join(new_narrs)}")

        return " | ".join(summary_parts)


# Singleton instance
_pattern_detector: Optional[PatternDetector] = None


def get_pattern_detector() -> PatternDetector:
    """Get or create the singleton PatternDetector instance."""
    global _pattern_detector
    if _pattern_detector is None:
        _pattern_detector = PatternDetector()
    return _pattern_detector
