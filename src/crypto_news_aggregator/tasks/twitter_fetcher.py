"""
Background task for fetching tweets.
"""
import asyncio
import logging
from ..services.twitter_service import twitter_service
from ..core.config import get_settings

logger = logging.getLogger(__name__)

class TwitterFetcher:
    """A class to fetch tweets from a rotating list of users, respecting rate limits."""

    def __init__(self):
        self.user_ids = []
        self.current_user_index = 0

    async def start(self):
        """Starts the tweet fetching loop."""
        # Initial resolution of user IDs
        self.user_ids = await twitter_service.resolve_user_ids()
        if not self.user_ids:
            logger.error("Could not resolve user IDs on startup. TwitterFetcher will not start.")
            return

        logger.info(f"Starting rotational tweet fetcher for users: {self.user_ids}")
        while True:
            try:
                # Determine which user to fetch next
                user_id_to_fetch = self.user_ids[self.current_user_index]
                logger.info(f"Next in rotation: user {user_id_to_fetch} at index {self.current_user_index}")

                # Get the latest tweet we have for this user to fetch incrementally
                since_id = await twitter_service.get_latest_tweet_id(user_id_to_fetch)
                
                # The service will handle the rate-limit waiting internally
                await twitter_service.fetch_tweets_from_user(user_id_to_fetch, since_id)

                # Move to the next user for the next cycle
                self.current_user_index = (self.current_user_index + 1) % len(self.user_ids)

            except Exception as e:
                logger.error(f"An error occurred in the TwitterFetcher loop: {e}")
                # Wait a bit before retrying to avoid fast failure loops
                await asyncio.sleep(60)

def get_twitter_fetcher() -> TwitterFetcher:
    """Initializes and returns a TwitterFetcher instance."""
    return TwitterFetcher()
