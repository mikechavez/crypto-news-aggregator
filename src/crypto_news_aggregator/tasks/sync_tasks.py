"""
Background tasks for database synchronization.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Optional

from ..services.sync_service import sync_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class SyncScheduler:
    """Scheduler for database synchronization tasks."""
    
    def __init__(self, interval: int = 300):
        """Initialize the sync scheduler.
        
        Args:
            interval: Sync interval in seconds (default: 5 minutes)
        """
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    async def _run_sync(self):
        """Run the synchronization task."""
        logger.info("Starting database synchronization task")
        
        while not self._stop_event.is_set():
            try:
                logger.info("Running database synchronization...")
                await sync_service.sync_all()
                logger.info(f"Database synchronization completed. Next sync in {self.interval} seconds.")
                
            except Exception as e:
                logger.error(f"Error during database synchronization: {str(e)}", exc_info=True)
                # Don't crash on error, just wait for the next interval
                
            # Wait for the next sync or until stopped
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval
                )
            except asyncio.TimeoutError:
                pass  # Continue with the next sync
    
    async def start(self):
        """Start the synchronization task."""
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run_sync())
            logger.info("Database synchronization task started")
    
    async def stop(self):
        """Stop the synchronization task."""
        if self._task and not self._task.done():
            self._stop_event.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Database synchronization task stopped")
    
    def __del__(self):
        """Ensure the task is stopped when the scheduler is destroyed."""
        if self._task and not self._task.done():
            self._task.cancel()


# Create a singleton instance with a default sync interval of 5 minutes (300 seconds)
sync_scheduler = SyncScheduler(interval=300)
