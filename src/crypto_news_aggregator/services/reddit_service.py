import praw
import asyncio
from typing import List
from crypto_news_aggregator.core.config import get_settings
from crypto_news_aggregator.models.article import ArticleCreate, ArticleMetrics, ArticleAuthor
from datetime import datetime

class RedditService:
    def __init__(self):
        settings = get_settings()
        if not all([settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET, settings.REDDIT_USER_AGENT]):
            raise ValueError("Reddit API credentials are not fully configured in your .env file.")

        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        self.subreddits = settings.REDDIT_SUBREDDITS

    async def fetch_posts(self, limit: int = 25) -> List[ArticleCreate]:
        """Asynchronously fetches posts from the configured subreddits."""
        loop = asyncio.get_event_loop()
        # PRAW is synchronous, so we run it in an executor
        return await loop.run_in_executor(None, self._fetch_posts_sync, limit)

    def _fetch_posts_sync(self, limit: int) -> List[ArticleCreate]:
        """Synchronous method to fetch posts."""
        all_posts = []
        for subreddit_name in self.subreddits:
            subreddit = self.reddit.subreddit(subreddit_name)
            for post in subreddit.hot(limit=limit):
                if not post.stickied:
                    article = self.parse_post(post)
                    all_posts.append(article)
        return all_posts

    def parse_post(self, post) -> ArticleCreate:
        """Parses a Reddit post into an ArticleCreate object."""
        author = ArticleAuthor(id=str(post.author.id), name=post.author.name) if post.author else None

        article = ArticleCreate(
            title=post.title,
            text=post.selftext,
            url=str(f"https://www.reddit.com{post.permalink}"),
            source_id=post.id,
            source='reddit',
            author=author,
            published_at=datetime.fromtimestamp(post.created_utc),
            metrics=ArticleMetrics(
                views=0, # Not directly available
                likes=post.score,
                replies=post.num_comments,
            ),
            raw_data={
                "id": post.id,
                "title": post.title,
                "score": post.score,
                "num_comments": post.num_comments,
                "selftext": post.selftext,
                "created_utc": post.created_utc,
                "url": post.url
            }
        )
        return article

async def main():
    reddit_service = RedditService()
    posts = await reddit_service.fetch_posts()
    for post in posts:
        print(f"Title: {post.title}")
        print(f"Source: {post.source}")
        print(f"URL: {post.url}")
        print("-"*20)

if __name__ == "__main__":
    # This requires your .env file to be correctly set up with Reddit credentials
    # You can obtain these from https://www.reddit.com/prefs/apps
    asyncio.run(main())
