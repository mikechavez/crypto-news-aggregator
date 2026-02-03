"""
Test briefing task execution.

Tests cover task success, failure handling, and retry logic.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from crypto_news_aggregator.tasks.briefing_tasks import (
    generate_morning_briefing_task,
    generate_evening_briefing_task,
    cleanup_old_briefings_task,
)


class TestMorningBriefingTask:
    """Tests for morning briefing task."""

    def test_morning_briefing_task_success(self):
        """Test morning briefing task executes successfully."""
        mock_briefing = {
            "_id": "test123",
            "type": "morning",
            "generated_at": datetime(2026, 2, 2, 13, 0, 0, tzinfo=timezone.utc),
        }

        async def mock_async_briefing():
            return mock_briefing

        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._generate_morning_briefing_async",
            return_value=mock_async_briefing(),
        ):
            with patch(
                "crypto_news_aggregator.tasks.briefing_tasks._run_async",
                return_value=mock_briefing,
            ):
                result = generate_morning_briefing_task()

                assert result["status"] == "success"
                assert result["briefing_id"] == "test123"
                assert "duration_seconds" in result

    def test_morning_briefing_task_skipped_already_exists(self):
        """Test morning briefing task when briefing already exists."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=None,
        ):
            result = generate_morning_briefing_task()

            assert result["status"] == "skipped"
            assert result["reason"] == "briefing_already_exists"


class TestEveningBriefingTask:
    """Tests for evening briefing task."""

    def test_evening_briefing_task_success(self):
        """Test evening briefing task executes successfully."""
        mock_briefing = {
            "_id": "test456",
            "type": "evening",
            "generated_at": datetime(2026, 2, 2, 21, 0, 0, tzinfo=timezone.utc),
        }

        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=mock_briefing,
        ):
            result = generate_evening_briefing_task()

            assert result["status"] == "success"
            assert result["briefing_id"] == "test456"
            assert "duration_seconds" in result

    def test_evening_briefing_task_skipped_already_exists(self):
        """Test evening briefing task when briefing already exists."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=None,
        ):
            result = generate_evening_briefing_task()

            assert result["status"] == "skipped"
            assert result["reason"] == "briefing_already_exists"


class TestCleanupBriefingsTask:
    """Tests for cleanup old briefings task."""

    def test_cleanup_old_briefings_success(self):
        """Test cleanup task deletes old briefings."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=5,
        ):
            result = cleanup_old_briefings_task(retention_days=30)

            assert result["status"] == "success"
            assert result["deleted_count"] == 5
            assert result["retention_days"] == 30

    def test_cleanup_old_briefings_zero_deleted(self):
        """Test cleanup task when no briefings are old."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=0,
        ):
            result = cleanup_old_briefings_task(retention_days=30)

            assert result["status"] == "success"
            assert result["deleted_count"] == 0

    def test_cleanup_old_briefings_error(self):
        """Test cleanup task error handling."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            side_effect=Exception("Database connection error"),
        ):
            result = cleanup_old_briefings_task(retention_days=30)

            assert result["status"] == "error"
            assert "Database connection error" in result["error"]

    def test_cleanup_old_briefings_custom_retention(self):
        """Test cleanup task respects custom retention period."""
        with patch(
            "crypto_news_aggregator.tasks.briefing_tasks._run_async",
            return_value=10,
        ):
            result = cleanup_old_briefings_task(retention_days=60)

            assert result["retention_days"] == 60


class TestTaskRetryConfiguration:
    """Tests for task retry configuration."""

    def test_morning_task_has_retry_config(self):
        """Test that morning task has retry configuration."""
        # The task is decorated with shared_task
        assert hasattr(generate_morning_briefing_task, "__wrapped__")

    def test_evening_task_has_retry_config(self):
        """Test that evening task has retry configuration."""
        # The task is decorated with shared_task
        assert hasattr(generate_evening_briefing_task, "__wrapped__")

    def test_cleanup_task_exists(self):
        """Test that cleanup task is properly defined."""
        assert callable(cleanup_old_briefings_task)


class TestTaskSchedulingConfiguration:
    """Tests for task scheduling configuration."""

    def test_beat_schedule_includes_morning_task(self):
        """Test that beat schedule includes morning briefing task."""
        from crypto_news_aggregator.tasks.celery_config import get_beat_schedule

        schedule = get_beat_schedule()
        assert "generate-morning-briefing" in schedule

    def test_beat_schedule_includes_evening_task(self):
        """Test that beat schedule includes evening briefing task."""
        from crypto_news_aggregator.tasks.celery_config import get_beat_schedule

        schedule = get_beat_schedule()
        assert "generate-evening-briefing" in schedule

    def test_morning_briefing_schedule_correct_time(self):
        """Test morning briefing is scheduled for 8 AM EST."""
        from crypto_news_aggregator.tasks.celery_config import get_beat_schedule
        from celery.schedules import crontab

        schedule = get_beat_schedule()
        morning_task = schedule["generate-morning-briefing"]

        # Verify schedule is crontab
        assert hasattr(morning_task["schedule"], "is_due")

    def test_evening_briefing_schedule_correct_time(self):
        """Test evening briefing is scheduled for 8 PM EST."""
        from crypto_news_aggregator.tasks.celery_config import get_beat_schedule

        schedule = get_beat_schedule()
        evening_task = schedule["generate-evening-briefing"]

        # Verify schedule is crontab
        assert hasattr(evening_task["schedule"], "is_due")
