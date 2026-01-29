"""
Memory Manager for the Briefing Agent.

Handles the hybrid memory system:
- MongoDB: Briefing history, patterns, manual inputs
- Markdown: Admin feedback file (human-editable)

The feedback file is the only file-based memory. All other memory
is stored in MongoDB for production reliability.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

from crypto_news_aggregator.db.operations.briefing import (
    get_briefings_last_n_days,
    get_recent_patterns,
    get_pending_manual_inputs,
)

logger = logging.getLogger(__name__)

# Default location for the feedback file
# In production, this should be a persistent volume or configurable path
BRIEFING_MEMORY_DIR = os.environ.get(
    "BRIEFING_MEMORY_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "briefing_memory")
)
FEEDBACK_FILE_PATH = os.path.join(BRIEFING_MEMORY_DIR, "briefing_feedback.md")

# Default feedback template
DEFAULT_FEEDBACK_TEMPLATE = """# Briefing Agent Feedback Log

This file contains training feedback for the briefing agent.
Edit this file directly to guide future briefing generation.

---

## Active Guidelines

### Focus Areas
- Prioritize regulatory developments and institutional moves
- Highlight entities that are NEW to discussions (not just trending)
- Always explain "why it matters" for each insight

### Tone & Style
- Professional analyst perspective - objective but with informed opinion
- Connect dots between events (causal relationships)
- Be direct about uncertainty when data is limited

### What to Avoid
- Minor protocol upgrades unless they have market significance
- Price movements without context (the "why" behind the move)
- Overly bullish/bearish language without justification

---

## Feedback History

(Add dated feedback entries below as briefings are reviewed)

"""


@dataclass
class MemoryContext:
    """Container for all memory context used by the briefing agent."""

    feedback: str
    history: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]]
    manual_inputs: List[Dict[str, Any]]

    def to_prompt_context(self) -> str:
        """Format memory context for inclusion in LLM prompt."""
        parts = []

        # Admin feedback/guidelines
        if self.feedback:
            parts.append("## Admin Feedback & Guidelines\n")
            parts.append(self.feedback)
            parts.append("\n")

        # Recent patterns
        if self.patterns:
            parts.append("## Recent Patterns Detected (Last 7 Days)\n")
            for pattern in self.patterns[:10]:  # Limit to 10 most recent
                parts.append(f"- [{pattern.get('pattern_type')}] {pattern.get('description')}\n")
            parts.append("\n")

        # Briefing history summary
        if self.history:
            parts.append("## Recent Briefing History\n")
            for briefing in self.history[:7]:  # Last 7 briefings
                gen_at = briefing.get("generated_at", "")
                if isinstance(gen_at, datetime):
                    gen_at = gen_at.strftime("%Y-%m-%d %H:%M")
                briefing_type = briefing.get("type", "unknown")
                key_insights = briefing.get("content", {}).get("key_insights", [])
                insights_str = "; ".join(key_insights[:3]) if key_insights else "No insights recorded"
                parts.append(f"- **{briefing_type.title()} ({gen_at})**: {insights_str}\n")
            parts.append("\n")

        # Manual inputs
        if self.manual_inputs:
            parts.append("## External Inputs to Consider\n")
            for inp in self.manual_inputs:
                title = inp.get("title", "Untitled")
                source_type = inp.get("source_type", "other")
                content = inp.get("content", "")[:200]  # Truncate
                notes = inp.get("admin_notes", "")
                parts.append(f"### {title} ({source_type})\n")
                parts.append(f"{content}...\n")
                if notes:
                    parts.append(f"*Admin note: {notes}*\n")
                parts.append("\n")

        return "".join(parts)


class MemoryManager:
    """
    Manages the briefing agent's memory system.

    Handles:
    - Reading admin feedback from markdown file
    - Querying historical briefings from MongoDB
    - Querying detected patterns from MongoDB
    - Querying pending manual inputs from MongoDB
    """

    def __init__(self, feedback_file_path: Optional[str] = None):
        """
        Initialize the memory manager.

        Args:
            feedback_file_path: Optional custom path to feedback file
        """
        self.feedback_file_path = feedback_file_path or FEEDBACK_FILE_PATH
        self._ensure_feedback_file_exists()

    def _ensure_feedback_file_exists(self) -> None:
        """Create the feedback file and directory if they don't exist."""
        try:
            path = Path(self.feedback_file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            if not path.exists():
                path.write_text(DEFAULT_FEEDBACK_TEMPLATE)
                logger.info(f"Created feedback file at {self.feedback_file_path}")
        except Exception as e:
            logger.warning(f"Could not create feedback file: {e}")

    def read_feedback(self) -> str:
        """
        Read the admin feedback file.

        Returns:
            Content of the feedback file, or empty string if not found
        """
        try:
            path = Path(self.feedback_file_path)
            if path.exists():
                return path.read_text()
            else:
                logger.warning(f"Feedback file not found at {self.feedback_file_path}")
                return ""
        except Exception as e:
            logger.error(f"Error reading feedback file: {e}")
            return ""

    def append_feedback(self, briefing_date: str, briefing_type: str, feedback: str) -> bool:
        """
        Append new feedback to the feedback file.

        Args:
            briefing_date: Date of the briefing (YYYY-MM-DD)
            briefing_type: "morning" or "evening"
            feedback: The feedback text

        Returns:
            True if successful
        """
        try:
            path = Path(self.feedback_file_path)
            current_content = path.read_text() if path.exists() else DEFAULT_FEEDBACK_TEMPLATE

            # Format new feedback entry
            entry = f"\n### [{briefing_date} - {briefing_type.title()} Briefing]\n"
            entry += "**Admin Feedback:**\n"
            for line in feedback.strip().split("\n"):
                entry += f"- {line}\n"
            entry += "\n"

            # Append to file
            path.write_text(current_content + entry)
            logger.info(f"Appended feedback for {briefing_date} {briefing_type}")
            return True

        except Exception as e:
            logger.error(f"Error appending feedback: {e}")
            return False

    async def load_memory(self, history_days: int = 7) -> MemoryContext:
        """
        Load all memory context for the briefing agent.

        Args:
            history_days: Number of days of history to load

        Returns:
            MemoryContext with all memory sources
        """
        # Read feedback file
        feedback = self.read_feedback()

        # Query MongoDB for history, patterns, and manual inputs
        history = await get_briefings_last_n_days(days=history_days)
        patterns = await get_recent_patterns(days=history_days)
        manual_inputs = await get_pending_manual_inputs()

        return MemoryContext(
            feedback=feedback,
            history=history,
            patterns=patterns,
            manual_inputs=manual_inputs,
        )

    def get_active_guidelines(self) -> str:
        """
        Extract just the active guidelines section from feedback.

        Returns:
            The active guidelines section, or empty string
        """
        feedback = self.read_feedback()

        # Parse out the Active Guidelines section
        if "## Active Guidelines" in feedback:
            start = feedback.find("## Active Guidelines")
            end = feedback.find("## Feedback History", start)
            if end == -1:
                end = len(feedback)
            return feedback[start:end].strip()

        return ""


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create the singleton MemoryManager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
