#!/usr/bin/env python3
"""
Test script for the price monitor service.

This script demonstrates how to use the PriceMonitor to check Bitcoin prices
and trigger alerts based on price movements.
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Coroutine, TypeVar, cast

# Define a generic type variable for MongoDB operation results
T = TypeVar("T")

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Verify the project root exists
if not (project_root / "src").exists():
    raise RuntimeError(f"Could not find 'src' directory in {project_root}")

# Verify we can import the config module
try:
    from src.crypto_news_aggregator.core.config import get_settings
except ImportError as e:
    print(f"Error importing config module: {e}")
    print(f"Python path: {sys.path}")
    print(f"Project root: {project_root}")
    print(f"Contents of project root: {os.listdir(project_root)}")
    if (project_root / "src").exists():
        print(f"Contents of src: {os.listdir(project_root / 'src')}")
    raise

from src.crypto_news_aggregator.db.mongodb import mongo_manager, initialize_mongodb
from src.crypto_news_aggregator.services.price_monitor import PriceMonitor
from src.crypto_news_aggregator.services.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Enable debug logging for our package
logging.getLogger("crypto_news_aggregator").setLevel(logging.DEBUG)


async def setup_test_alerts() -> bool:
    """Set up test alerts in the database with enhanced error handling."""
    print("\n[setup_test_alerts] Starting test alerts setup...")

    # Log current task and event loop info
    try:
        current_task = asyncio.current_task()
        loop = asyncio.get_event_loop()
        print(
            f"[setup_test_alerts] Running in task: {current_task.get_name() if current_task else 'None'}"
        )
        print(f"[setup_test_alerts] Event loop ID: {id(loop)}")
    except Exception as e:
        print(f"[setup_test_alerts] Error getting task/loop info: {e}")

    try:
        # Get the alerts collection with retry logic
        print("[setup_test_alerts] Getting alerts collection...")

        async def _get_collection():
            return await mongo_manager.get_async_collection("alerts")

        alerts_collection = await run_mongodb_operation(
            _get_collection, "get_alerts_collection"
        )

        # Create a test user
        user_id = "test_user_123"

        # Create some test alerts with timezone-aware datetimes
        now = datetime.now(timezone.utc)
        print(f"[setup_test_alerts] Creating test alerts at {now}")

        test_alerts = [
            {
                "user_id": user_id,
                "crypto_id": "bitcoin",
                "condition": "ABOVE",
                "threshold": 50000.0,
                "is_active": True,
                "created_at": now,
                "last_triggered": None,
                "test_data": True,
            },
            {
                "user_id": user_id,
                "crypto_id": "bitcoin",
                "condition": "BELOW",
                "threshold": 40000.0,
                "is_active": True,
                "created_at": now,
                "last_triggered": None,
                "test_data": True,
            },
            {
                "user_id": user_id,
                "crypto_id": "bitcoin",
                "condition": "PERCENT_UP",
                "threshold": 5.0,
                "is_active": True,
                "created_at": now,
                "last_triggered": None,
                "test_data": True,
            },
            {
                "user_id": user_id,
                "crypto_id": "bitcoin",
                "condition": "PERCENT_DOWN",
                "threshold": 3.0,
                "is_active": True,
                "created_at": now,
                "last_triggered": None,
                "test_data": True,
            },
        ]

        # Delete existing test alerts with retry logic
        print("[setup_test_alerts] Deleting existing test alerts...")

        async def _delete_alerts():
            return await alerts_collection.delete_many({"test_data": True})

        delete_result = await run_mongodb_operation(
            _delete_alerts, "delete_test_alerts"
        )
        print(
            f"[setup_test_alerts] Deleted {delete_result.deleted_count} existing test alerts"
        )

        # Insert new test alerts with retry logic
        print("[setup_test_alerts] Inserting new test alerts...")

        async def _insert_alerts():
            return await alerts_collection.insert_many(test_alerts)

        result = await run_mongodb_operation(_insert_alerts, "insert_test_alerts")
        print(f"[setup_test_alerts] Inserted {len(result.inserted_ids)} test alerts")

        # Verify the alerts were inserted
        count = await alerts_collection.count_documents({"test_data": True})
        print(f"[setup_test_alerts] Verified {count} test alerts in database")

        if count != len(test_alerts):
            raise ValueError(f"Expected {len(test_alerts)} test alerts, found {count}")

        print("[setup_test_alerts] Test alerts setup completed successfully")
        return True

    except asyncio.CancelledError:
        print("[setup_test_alerts] Operation was cancelled")
        raise
    except Exception as e:
        print(f"[setup_test_alerts] Error in setup_test_alerts: {e}")
        import traceback

        traceback.print_exc()
        return False


def create_async_task(coro):
    """Helper to create an async task in the current event loop."""
    loop = asyncio.get_event_loop()
    return loop.create_task(coro)


async def run_mongodb_operation(
    operation_coro: Callable[[], Coroutine[Any, Any, T]],
    operation_name: str,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> T:
    """Run a MongoDB operation with retry logic and proper error handling."""
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            # Get the current event loop for this operation
            loop = asyncio.get_event_loop()
            print(
                f"[MongoDB] Running operation '{operation_name}' on loop {id(loop)} (attempt {attempt}/{max_retries})"
            )

            # Run the operation in a task to ensure it's scheduled on the current loop
            task = loop.create_task(operation_coro())
            result = await task
            return result

        except asyncio.CancelledError:
            print("[MongoDB] Operation was cancelled")
            raise

        except Exception as e:
            last_error = e
            if attempt == max_retries:
                print(
                    f"[MongoDB] Operation '{operation_name}' failed after {max_retries} attempts"
                )
                raise

            print(f"[MongoDB] Attempt {attempt} failed for '{operation_name}': {e}")
            print("Stack trace:")
            traceback.print_exc()
            print(f"Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)

    # This should never be reached because we raise in the loop, but mypy needs it
    raise cast(Exception, last_error)


async def initialize_application():
    """Initialize the application components."""
    print("\n=== Initializing Application ===")

    # Initialize MongoDB
    print("Initializing MongoDB...")
    try:
        if not await initialize_mongodb():
            print("Failed to initialize MongoDB.")
            return False
        print("MongoDB initialized successfully")
    except Exception as e:
        print(f"Error initializing MongoDB: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def run_monitor():
    """Run the price monitor with test data."""
    print("\n=== Bitcoin Price Monitor Test ===")
    print("This script will:")
    print("1. Initialize application components")
    print("2. Set up test alert conditions")
    print("3. Start monitoring Bitcoin prices")
    print("4. Trigger notifications when conditions are met")
    print("Press Ctrl+C to stop the monitor\n")

    # Get current event loop for debugging
    loop = asyncio.get_event_loop()
    print(f"\n[run_monitor] Current event loop: {id(loop)}")

    # Register cleanup on exit
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(cleanup_and_exit()))

    # Initialize application components
    if not await initialize_application():
        print("Failed to initialize application components. Exiting...")
        return

    # Set up signal handling for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        print("\nShutting down gracefully...")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Set up test alerts
        print("[run_monitor] Setting up test alerts...")
        success = await setup_test_alerts()
        if not success:
            print("\n[run_monitor] Failed to set up test alerts. Exiting.")
            await cleanup()
            return

        # Create and start the price monitor
        monitor = PriceMonitor()

        # Run the monitor
        print("\n[run_monitor] Starting price monitor...")
        print("Monitoring for price alerts. Press Ctrl+C to stop.")

        # Run the monitor in the background
        monitor_task = create_async_task(monitor.start())

        try:
            # Wait for shutdown signal or error
            while not shutdown_event.is_set() and not monitor_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(monitor_task), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"\n[run_monitor] Error in monitor task: {e}")
                    break

            # If we get here, either shutdown was requested or an error occurred
            if not monitor_task.done():
                print("\n[run_monitor] Stopping monitor...")
                monitor.stop()
                try:
                    await asyncio.wait_for(monitor_task, timeout=5.0)
                except asyncio.TimeoutError:
                    print("[run_monitor] Warning: Monitor did not stop gracefully")
                except Exception as e:
                    print(f"[run_monitor] Error while stopping monitor: {e}")

            print("[run_monitor] Monitor stopped")

        except asyncio.CancelledError:
            print("\n[run_monitor] Received cancellation, cleaning up...")
            if not monitor_task.done():
                monitor.stop()
                try:
                    await asyncio.wait_for(monitor_task, timeout=5.0)
                except (asyncio.TimeoutError, Exception) as e:
                    print(f"[run_monitor] Error during cleanup: {e}")
            raise

    except Exception as e:
        print(f"\n[run_monitor] Error in run_monitor: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n[run_monitor] Cleaning up...")
        await cleanup()


async def initialize_mongodb():
    """Initialize the MongoDB connection."""
    try:
        print("Initializing MongoDB connection...")
        if (
            not hasattr(mongo_manager, "_async_client")
            or mongo_manager._async_client is None
        ):
            await mongo_manager.initialize()

            # Verify the connection
            try:
                await mongo_manager.async_client.admin.command("ping")
                print("MongoDB connection verified")
            except Exception as e:
                print(f"Failed to verify MongoDB connection: {e}")
                return False

        print("MongoDB initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize MongoDB: {e}")
        return False


async def cleanup_and_exit(exit_code: int = 0):
    """Clean up resources and exit the script."""
    await cleanup()
    print("Exiting...")
    sys.exit(exit_code)


async def main_async():
    """Async entry point for the application."""
    try:
        await run_monitor()
    except asyncio.CancelledError:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await cleanup()


def main():
    """Run the monitor in the main event loop."""
    try:
        # Run the main async function
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\nScript execution completed")


async def cleanup():
    """Clean up resources and close MongoDB connections."""
    print("\n[cleanup] Starting cleanup...")

    # Close MongoDB connection if it exists
    if (
        hasattr(mongo_manager, "_async_client")
        and mongo_manager._async_client is not None
    ):
        print("[cleanup] Closing MongoDB connection...")
        try:
            mongo_manager._async_client.close()
            print("[cleanup] MongoDB connection closed")
        except Exception as e:
            print(f"[cleanup] Error closing MongoDB connection: {e}")
        finally:
            mongo_manager._async_client = None

    # Cancel any remaining tasks
    try:
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            print(f"[cleanup] Cancelling {len(pending)} pending tasks...")
            for task in pending:
                if not task.done():
                    task.cancel()

            # Allow tasks to handle cancellation
            await asyncio.gather(*pending, return_exceptions=True)
    except Exception as e:
        print(f"[cleanup] Error during task cleanup: {e}")

    print("[cleanup] Cleanup complete")


def create_mongodb_client():
    """Create a new MongoDB client instance."""
    from src.crypto_news_aggregator.core.config import settings

    return AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        maxPoolSize=100,
        minPoolSize=1,
        maxIdleTimeMS=60000,
    )


if __name__ == "__main__":
    try:
        # Run the main function
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Ensure cleanup runs on script exit
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.run_until_complete(cleanup())
            loop.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        print("Script execution completed")
