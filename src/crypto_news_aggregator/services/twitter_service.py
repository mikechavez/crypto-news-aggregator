"""
Service for collecting and processing data from Twitter.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from tweepy.asynchronous import AsyncClient
from tweepy import Tweet, User
from datetime import datetime, timedelta, timezone
from ..core.config import get_settings
from ..db.mongodb import mongo_manager, COLLECTION_TWEETS
from ..models.tweet import TweetCreate, TweetInDB
from ..llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

class TwitterService:
    """Service for handling Twitter data collection."""

    def __init__(self):
        self.settings = get_settings()
        self.api = AsyncClient(self.settings.TWITTER_BEARER_TOKEN)
        self.collection = None
        self.llm_provider = get_llm_provider()
        self.target_usernames = ["WatcherGuru", "lookonchain", "glassnode", "BittelJulien"]
        self.user_ids = []
        self.last_request_time: Optional[datetime] = None
        self.request_interval = timedelta(minutes=15)

    async def _get_collection(self):
        if self.collection is None:
            self.collection = await mongo_manager.get_async_collection(COLLECTION_TWEETS)
        return self.collection

    async def _make_api_call(self, api_call, *args, **kwargs):
        """A centralized method to handle API calls with rate-limit awareness."""
        if self.last_request_time:
            time_since_last_request = datetime.now(timezone.utc) - self.last_request_time
            if time_since_last_request < self.request_interval:
                wait_time = (self.request_interval - time_since_last_request).total_seconds()
                logger.info(f"Rate limit pre-emptive wait: sleeping for {wait_time:.2f} seconds.")
                await asyncio.sleep(wait_time)
                logger.info("Finished pre-emptive sleep.")
        
        self.last_request_time = datetime.now(timezone.utc)
        return await api_call(*args, **kwargs)

    async def resolve_user_ids(self) -> List[str]:
        """Resolves usernames to user IDs and returns them."""
        if not self.target_usernames:
            return []
        for attempt in range(4):  # Try up to 4 times (initial + 3 retries)
            try:
                users_response = await self._make_api_call(self.api.get_users, usernames=self.target_usernames)
                if users_response and users_response.data:
                    self.user_ids = [user.id for user in users_response.data]
                    logger.info(f"Successfully resolved {len(self.user_ids)} user IDs: {self.user_ids}")
                    return self.user_ids
                else:
                    logger.warning("User ID resolution returned no data.")
                    return [] # No users found, not an error
            except Exception as e:
                if "429" in str(e):
                    wait_time = 910  # Wait 15 minutes and 10 seconds
                    logger.warning(f"Rate limit hit on user resolution. Attempt {attempt + 1}/4. Retrying in {wait_time} seconds...")
                    if attempt < 3:
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"An unexpected error occurred during user resolution: {e}")
                    break # Break on non-rate-limit errors

        logger.error("Failed to resolve user IDs after multiple retries.")
        return []

    async def get_latest_tweet_id(self, author_id: str) -> Optional[str]:
        """Gets the most recent tweet ID for a given author from the database."""
        collection = await self._get_collection()
        latest_tweet = await collection.find_one(
            {"author.id": author_id},
            sort=[("tweet_created_at", -1)]
        )
        if latest_tweet:
            return latest_tweet.get("tweet_id")
        return None

    async def fetch_tweets_from_user(self, user_id: str, since_id: Optional[str] = None):
        """Fetches recent tweets from a specific user, optionally since a specific tweet ID."""
        logger.info(f"Fetching tweets for user {user_id} since ID: {since_id}")
        try:
            response = await self._make_api_call(
                self.api.get_users_tweets,
                id=user_id,
                since_id=since_id,
                tweet_fields=["created_at", "public_metrics", "lang", "author_id"],
                expansions=["author_id"],
                max_results=100
            )
            if response.data:
                logger.info(f"Found {len(response.data)} new tweets for user {user_id}.")
                for tweet in response.data:
                    await self.store_tweet(tweet)
            else:
                logger.info(f"No new tweets found for user {user_id}.")
        except Exception as e:
            logger.error(f"Error fetching tweets for user {user_id}: {e}")


    async def store_tweet(self, tweet: Tweet, author: Optional[User] = None) -> Optional[TweetInDB]:
        """Transforms and stores a single tweet in the database, avoiding duplicates."""
        collection = await self._get_collection()

        # Deduplication check
        existing_tweet = await collection.find_one({"tweet_id": str(tweet.id)})
        if existing_tweet:
            logger.debug(f"Tweet {tweet.id} already exists. Skipping.")
            return None

        if author is None:
            # If author is not provided (e.g. from user_tweets endpoint), fetch it
            try:
                user_response = await self.api.get_user(id=tweet.author_id, user_fields=["id", "name", "username"])
                if user_response.data:
                    author = user_response.data
                else:
                    logger.warning(f"Could not fetch author for tweet {tweet.id}")
                    return None
            except Exception as e:
                logger.error(f"Error fetching author for tweet {tweet.id}: {e}")
                return None

        relevance_score = self.llm_provider.score_relevance(tweet.text)
        sentiment_score = self.llm_provider.analyze_sentiment(tweet.text)

        def get_sentiment_label(score: float) -> str:
            if score > 0.3:
                return "bullish"
            elif score < -0.3:
                return "bearish"
            else:
                return "neutral"

        sentiment_label = get_sentiment_label(sentiment_score)

        tweet_data = {
            "tweet_id": str(tweet.id),
            "text": tweet.text,
            "author": {
                "id": str(author.id),
                "name": author.name,
                "username": author.username,
            },
            "url": f"https://twitter.com/{author.username}/status/{tweet.id}",
            "lang": tweet.lang,
            "metrics": {
                "impressions": tweet.public_metrics.get("impression_count", 0),
                "likes": tweet.public_metrics.get("like_count", 0),
                "retweets": tweet.public_metrics.get("retweet_count", 0),
                "replies": tweet.public_metrics.get("reply_count", 0),
                "quotes": tweet.public_metrics.get("quote_count", 0),
            },
            "keywords": [], # Keywords are now implicitly handled by which user is being monitored
            "relevance_score": relevance_score,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "raw_data": tweet.data,
            "tweet_created_at": tweet.created_at
        }

        try:
            tweet_to_create = TweetCreate(**tweet_data)
            result = await collection.insert_one(tweet_to_create.model_dump(by_alias=True))
            if result.inserted_id:
                created_tweet = await collection.find_one({"_id": result.inserted_id})
                logger.info(f"Stored tweet {tweet.id}")
                return TweetInDB(**created_tweet)
        except Exception as e:
            logger.error(f"Error storing tweet {tweet.id}: {e}")
        
        return None

# Singleton instance
twitter_service = TwitterService()
