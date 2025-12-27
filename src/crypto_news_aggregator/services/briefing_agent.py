"""
Briefing Agent Service for generating daily crypto briefings.

This is the main orchestration service that:
- Loads memory context (feedback, history, patterns)
- Gathers current signals and narratives
- Detects patterns in market data
- Uses LLM to generate narrative briefings
- Implements the self-refine pattern for quality

Architecture: Memory-Augmented ReAct + Self-Refine (single agent)
"""

import json
import logging
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.db.mongodb import mongo_manager
from crypto_news_aggregator.db.operations.briefing import (
    insert_briefing,
    insert_pattern,
    check_briefing_exists_for_slot,
    get_latest_briefing,
)
from crypto_news_aggregator.services.memory_manager import (
    get_memory_manager,
    MemoryContext,
)
from crypto_news_aggregator.services.pattern_detector import (
    get_pattern_detector,
    PatternSummary,
)

logger = logging.getLogger(__name__)

# LLM Configuration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-3-haiku-20240307"
FALLBACK_MODELS = [
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
]


@dataclass
class BriefingInput:
    """Input data for briefing generation."""

    briefing_type: str  # "morning" or "evening"
    signals: List[Dict[str, Any]]
    narratives: List[Dict[str, Any]]
    patterns: PatternSummary
    memory: MemoryContext
    generated_at: datetime


@dataclass
class GeneratedBriefing:
    """Output from briefing generation."""

    narrative: str
    key_insights: List[str]
    entities_mentioned: List[str]
    detected_patterns: List[str]
    recommendations: List[Dict[str, str]]
    confidence_score: float


class BriefingAgent:
    """
    AI-powered briefing agent that generates daily crypto briefings.

    Uses a single-agent architecture with:
    - Memory augmentation from feedback and history
    - Pattern detection for market insights
    - Self-refine loop for quality assurance
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the briefing agent.

        Args:
            api_key: Anthropic API key (defaults to settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        self.memory_manager = get_memory_manager()
        self.pattern_detector = get_pattern_detector()

    async def generate_briefing(
        self,
        briefing_type: str = "morning",
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a new briefing.

        Args:
            briefing_type: "morning" or "evening"
            force: If True, generate even if one already exists for this slot

        Returns:
            Generated briefing document or None if skipped/failed
        """
        now = datetime.now(timezone.utc)

        # Check if briefing already exists for this slot
        if not force:
            exists = await check_briefing_exists_for_slot(briefing_type, now)
            if exists:
                logger.info(f"{briefing_type.title()} briefing already exists for today")
                return None

        logger.info(f"Starting {briefing_type} briefing generation")

        try:
            # Step 1: Gather inputs
            briefing_input = await self._gather_inputs(briefing_type, now)

            # Step 2: Generate initial briefing
            generated = await self._generate_with_llm(briefing_input)

            # Step 3: Self-refine (quality check)
            refined = await self._self_refine(generated, briefing_input)

            # Step 4: Save briefing to database
            briefing_doc = await self._save_briefing(
                briefing_type, briefing_input, refined
            )

            # Step 5: Save detected patterns
            await self._save_patterns(briefing_doc["_id"], briefing_input.patterns)

            logger.info(f"Successfully generated {briefing_type} briefing")
            return briefing_doc

        except Exception as e:
            logger.exception(f"Failed to generate {briefing_type} briefing: {e}")
            return None

    async def _gather_inputs(
        self, briefing_type: str, now: datetime
    ) -> BriefingInput:
        """Gather all inputs needed for briefing generation."""
        # Load memory context
        memory = await self.memory_manager.load_memory(history_days=7)
        logger.info(
            f"Loaded memory: {len(memory.history)} history items, "
            f"{len(memory.patterns)} patterns, {len(memory.manual_inputs)} manual inputs"
        )

        # Get current signals
        signals = await self._get_trending_signals()
        logger.info(f"Retrieved {len(signals)} trending signals")

        # Get current narratives
        narratives = await self._get_active_narratives()
        logger.info(f"Retrieved {len(narratives)} active narratives")

        # Detect patterns
        patterns = await self.pattern_detector.detect_all_patterns(
            current_signals=signals,
            current_narratives=narratives,
            history=memory.history,
        )
        logger.info(
            f"Detected patterns: {len(patterns.entity_surges)} surges, "
            f"{len(patterns.sentiment_shifts)} sentiment shifts, "
            f"{len(patterns.expected_events)} expected events, "
            f"{len(patterns.narrative_emergences)} emergences"
        )

        return BriefingInput(
            briefing_type=briefing_type,
            signals=signals,
            narratives=narratives,
            patterns=patterns,
            memory=memory,
            generated_at=now,
        )

    async def _get_trending_signals(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top trending signals from the database."""
        db = await mongo_manager.get_async_database()
        collection = db.trending_signals

        # Get signals from last 24 hours, sorted by score
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        cursor = collection.find(
            {"updated_at": {"$gte": cutoff}},
            sort=[("metrics.score_24h", -1)],
        ).limit(limit)

        signals = await cursor.to_list(length=limit)
        return signals

    async def _get_active_narratives(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Get active narratives from the database."""
        db = await mongo_manager.get_async_database()
        collection = db.narratives

        # Get narratives that are not dormant
        active_states = ["emerging", "rising", "hot", "cooling", "echo", "reactivated"]

        cursor = collection.find(
            {"lifecycle_state": {"$in": active_states}},
            sort=[("recency_score", -1), ("mention_velocity", -1)],
        ).limit(limit)

        narratives = await cursor.to_list(length=limit)
        return narratives

    async def _generate_with_llm(
        self, briefing_input: BriefingInput
    ) -> GeneratedBriefing:
        """Generate briefing content using LLM."""
        prompt = self._build_generation_prompt(briefing_input)

        response_text = await self._call_llm(
            prompt,
            system_prompt=self._get_system_prompt(briefing_input.briefing_type),
            max_tokens=4096,
        )

        return self._parse_briefing_response(response_text)

    async def _self_refine(
        self,
        generated: GeneratedBriefing,
        briefing_input: BriefingInput,
    ) -> GeneratedBriefing:
        """
        Self-refine the generated briefing for quality.

        This implements the self-refine pattern:
        1. Evaluate the initial output
        2. Identify issues
        3. Refine if needed
        """
        # Build critique prompt
        critique_prompt = self._build_critique_prompt(generated, briefing_input)

        critique_response = await self._call_llm(
            critique_prompt,
            system_prompt="You are a crypto market analyst reviewing a briefing for quality.",
            max_tokens=1024,
        )

        # Check if refinement is needed
        needs_refinement = self._check_needs_refinement(critique_response)

        if not needs_refinement:
            logger.info("Briefing passed quality check, no refinement needed")
            return generated

        logger.info("Briefing needs refinement, running refinement pass")

        # Build refinement prompt
        refinement_prompt = self._build_refinement_prompt(
            generated, critique_response, briefing_input
        )

        refined_response = await self._call_llm(
            refinement_prompt,
            system_prompt=self._get_system_prompt(briefing_input.briefing_type),
            max_tokens=4096,
        )

        return self._parse_briefing_response(refined_response)

    def _get_system_prompt(self, briefing_type: str) -> str:
        """Get the system prompt for briefing generation."""
        time_context = "morning" if briefing_type == "morning" else "evening"

        return f"""You are a senior crypto market analyst writing a {time_context} briefing memo.

Your role is to synthesize market signals, narratives, and patterns into an insightful,
actionable briefing for sophisticated crypto market participants.

Writing Style:
- Professional analyst perspective - objective but with informed opinion
- Write as a flowing narrative memo, NOT bullet points
- Connect dots between events (causal relationships)
- Be direct about uncertainty when data is limited
- Include your professional "read" on situations with reasoning
- Explain "why it matters" for each major insight

Focus Areas:
- Prioritize regulatory developments and institutional moves
- Highlight entities that are NEW to discussions (not just trending)
- When major expected events exist (Fed, SEC, ETF decisions), always mention them

What to Avoid:
- Minor protocol upgrades unless they have market significance
- Price movements without context (the "why" behind the move)
- Overly bullish/bearish language without justification
- Generic market commentary without specific insights

Output Format:
Return valid JSON with this structure:
{{
    "narrative": "The main briefing narrative as flowing prose...",
    "key_insights": ["insight1", "insight2", "insight3"],
    "entities_mentioned": ["entity1", "entity2"],
    "detected_patterns": ["pattern description 1", "pattern description 2"],
    "recommendations": [
        {{"title": "Article/Narrative Title", "theme": "theme_name"}},
    ],
    "confidence_score": 0.85
}}"""

    def _build_generation_prompt(self, briefing_input: BriefingInput) -> str:
        """Build the main generation prompt."""
        parts = []

        # Time context
        time_str = briefing_input.generated_at.strftime("%A, %B %d, %Y")
        parts.append(f"Generate the {briefing_input.briefing_type} crypto briefing for {time_str}.\n")

        # Memory context (feedback and guidelines)
        memory_context = briefing_input.memory.to_prompt_context()
        if memory_context:
            parts.append(memory_context)

        # Current signals
        if briefing_input.signals:
            parts.append("\n## Current Trending Signals\n")
            for signal in briefing_input.signals[:10]:
                entity = signal.get("entity", "Unknown")
                score = signal.get("metrics", {}).get("score_24h", 0)
                velocity = signal.get("metrics", {}).get("velocity_24h", 0)
                parts.append(f"- {entity}: score={score:.1f}, velocity={velocity:.0f}%\n")

        # Current narratives
        if briefing_input.narratives:
            parts.append("\n## Active Narratives\n")
            for narrative in briefing_input.narratives[:8]:
                title = narrative.get("title", "Untitled")
                theme = narrative.get("theme", "unknown")
                lifecycle = narrative.get("lifecycle_state", "unknown")
                momentum = narrative.get("momentum", "unknown")
                parts.append(f"- **{title}** ({theme}): {lifecycle}, momentum: {momentum}\n")

        # Detected patterns
        patterns_context = briefing_input.patterns.to_prompt_context()
        if patterns_context:
            parts.append("\n")
            parts.append(patterns_context)

        # Manual inputs
        if briefing_input.memory.manual_inputs:
            parts.append("\n## External Inputs to Consider\n")
            for inp in briefing_input.memory.manual_inputs[:3]:
                title = inp.get("title", "Untitled")
                content = inp.get("content", "")[:200]
                parts.append(f"### {title}\n{content}...\n\n")

        parts.append("\nGenerate the briefing narrative now. Return ONLY valid JSON.")

        return "".join(parts)

    def _build_critique_prompt(
        self, generated: GeneratedBriefing, briefing_input: BriefingInput
    ) -> str:
        """Build prompt for self-critique."""
        return f"""Review this crypto briefing for quality issues:

BRIEFING NARRATIVE:
{generated.narrative}

KEY INSIGHTS:
{json.dumps(generated.key_insights, indent=2)}

DETECTED PATTERNS:
{json.dumps(generated.detected_patterns, indent=2)}

Check for these issues:
1. Missing context: Are major patterns/events mentioned but not explained?
2. Unsupported claims: Are there statements without evidence from the data?
3. Missing connections: Are there obvious connections between events that weren't made?
4. Repetition from history: Does this repeat insights from recent briefings without new context?
5. Tone issues: Is it too bullish/bearish without justification?

Respond with:
{{
    "needs_refinement": true/false,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}"""

    def _check_needs_refinement(self, critique_response: str) -> bool:
        """Check if the critique indicates refinement is needed."""
        try:
            # Try to parse JSON response
            import re
            json_match = re.search(r"\{.*\}", critique_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("needs_refinement", False)
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback: check for keywords
        lower_response = critique_response.lower()
        refinement_keywords = ["needs refinement", "should be improved", "issues found", "missing"]
        return any(kw in lower_response for kw in refinement_keywords)

    def _build_refinement_prompt(
        self,
        generated: GeneratedBriefing,
        critique: str,
        briefing_input: BriefingInput,
    ) -> str:
        """Build prompt for refinement pass."""
        return f"""Refine this crypto briefing based on the critique feedback:

ORIGINAL BRIEFING:
{generated.narrative}

CRITIQUE FEEDBACK:
{critique}

AVAILABLE DATA:
- Signals: {len(briefing_input.signals)} trending entities
- Narratives: {len(briefing_input.narratives)} active narratives
- Patterns: {len(briefing_input.patterns.all_patterns())} detected patterns

Address the issues identified in the critique and generate an improved briefing.
Return ONLY valid JSON in the same format as before."""

    def _parse_briefing_response(self, response_text: str) -> GeneratedBriefing:
        """Parse LLM response into GeneratedBriefing."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text

            # Clean up the JSON string - replace literal newlines in string values
            # This handles cases where the LLM outputs multi-line strings
            # Replace actual newlines with escaped newlines for valid JSON
            cleaned_json = ""
            in_string = False
            escape_next = False
            for char in json_str:
                if escape_next:
                    cleaned_json += char
                    escape_next = False
                elif char == '\\':
                    cleaned_json += char
                    escape_next = True
                elif char == '"':
                    cleaned_json += char
                    in_string = not in_string
                elif in_string and char == '\n':
                    cleaned_json += '\\n'
                elif in_string and char == '\r':
                    cleaned_json += '\\r'
                elif in_string and char == '\t':
                    cleaned_json += '\\t'
                else:
                    cleaned_json += char

            data = json.loads(cleaned_json)

            return GeneratedBriefing(
                narrative=data.get("narrative", ""),
                key_insights=data.get("key_insights", []),
                entities_mentioned=data.get("entities_mentioned", []),
                detected_patterns=data.get("detected_patterns", []),
                recommendations=data.get("recommendations", []),
                confidence_score=data.get("confidence_score", 0.7),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")

            # Return minimal briefing
            return GeneratedBriefing(
                narrative=response_text[:2000] if response_text else "Failed to generate briefing.",
                key_insights=[],
                entities_mentioned=[],
                detected_patterns=[],
                recommendations=[],
                confidence_score=0.3,
            )

    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        """Call the LLM API with fallback models."""
        models_to_try = [DEFAULT_MODEL] + FALLBACK_MODELS

        for model in models_to_try:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        ANTHROPIC_API_URL,
                        headers={
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json",
                        },
                        json={
                            "model": model,
                            "max_tokens": max_tokens,
                            "system": system_prompt,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                        timeout=120,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if model != DEFAULT_MODEL:
                        logger.info(f"Using fallback model: {model}")

                    return data.get("content", [{}])[0].get("text", "")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    logger.warning(f"403 Forbidden for model {model}, trying fallback...")
                    continue
                logger.error(f"LLM API error: {e.response.status_code}")
                raise
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                raise

        raise RuntimeError("All LLM models failed")

    async def _save_briefing(
        self,
        briefing_type: str,
        briefing_input: BriefingInput,
        generated: GeneratedBriefing,
    ) -> Dict[str, Any]:
        """Save the generated briefing to the database."""
        from bson import ObjectId

        briefing_doc = {
            "type": briefing_type,
            "generated_at": briefing_input.generated_at,
            "version": "2.0",  # Agent-generated briefings
            "content": {
                "narrative": generated.narrative,
                "key_insights": generated.key_insights,
                "entities_mentioned": generated.entities_mentioned,
                "detected_patterns": generated.detected_patterns,
                "recommendations": generated.recommendations,
            },
            "metadata": {
                "confidence_score": generated.confidence_score,
                "signal_count": len(briefing_input.signals),
                "narrative_count": len(briefing_input.narratives),
                "pattern_count": len(briefing_input.patterns.all_patterns()),
                "manual_input_count": len(briefing_input.memory.manual_inputs),
                "model": DEFAULT_MODEL,
            },
        }

        briefing_id = await insert_briefing(briefing_doc)
        briefing_doc["_id"] = ObjectId(briefing_id)

        logger.info(f"Saved briefing {briefing_id}")
        return briefing_doc

    async def _save_patterns(
        self, briefing_id: str, patterns: PatternSummary
    ) -> None:
        """Save detected patterns to the database."""
        for pattern in patterns.all_patterns():
            pattern_doc = {
                "briefing_id": briefing_id,
                "pattern_type": pattern.pattern_type,
                "description": pattern.description,
                "entities": pattern.entities,
                "confidence": pattern.confidence,
                "details": pattern.details,
            }
            await insert_pattern(pattern_doc)

        logger.info(f"Saved {len(patterns.all_patterns())} patterns for briefing {briefing_id}")


# Singleton instance
_briefing_agent: Optional[BriefingAgent] = None


def get_briefing_agent() -> BriefingAgent:
    """Get or create the singleton BriefingAgent instance."""
    global _briefing_agent
    if _briefing_agent is None:
        _briefing_agent = BriefingAgent()
    return _briefing_agent


async def generate_morning_briefing(force: bool = False) -> Optional[Dict[str, Any]]:
    """Convenience function to generate morning briefing."""
    agent = get_briefing_agent()
    return await agent.generate_briefing("morning", force=force)


async def generate_evening_briefing(force: bool = False) -> Optional[Dict[str, Any]]:
    """Convenience function to generate evening briefing."""
    agent = get_briefing_agent()
    return await agent.generate_briefing("evening", force=force)
