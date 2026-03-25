"""
Twitter/X scraper for @Yellow__Korea using Twitter API v2.
Falls back to Nitter RSS if API credentials are not available.
"""

import logging
import os
import aiohttp
import tweepy
from datetime import datetime, timezone

from src.config import TWITTER_BEARER_TOKEN, TWITTER_USERNAME, LAST_TWEET_FILE, DATA_DIR

logger = logging.getLogger(__name__)


def get_last_tweet_id() -> str | None:
    """Read the last processed tweet ID from file."""
    try:
        if os.path.exists(LAST_TWEET_FILE):
            with open(LAST_TWEET_FILE, "r") as f:
                tweet_id = f.read().strip()
                return tweet_id if tweet_id else None
    except Exception as e:
        logger.error(f"Error reading last tweet ID: {e}")
    return None


def save_last_tweet_id(tweet_id: str) -> None:
    """Save the last processed tweet ID to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_TWEET_FILE, "w") as f:
        f.write(str(tweet_id))


class TwitterScraper:
    """Scrapes tweets from @Yellow__Korea using Twitter API v2."""

    def __init__(self):
        self.username = TWITTER_USERNAME
        self.client = None
        self.user_id = None

        if TWITTER_BEARER_TOKEN:
            self.client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
            logger.info("Twitter API v2 client initialized")
        else:
            logger.warning("No Twitter Bearer Token. Using RSS fallback.")

    async def _get_user_id(self) -> str | None:
        """Get Twitter user ID from username."""
        if self.user_id:
            return self.user_id
        if not self.client:
            return None
        try:
            user = self.client.get_user(username=self.username)
            if user and user.data:
                self.user_id = str(user.data.id)
                return self.user_id
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
        return None

    async def fetch_latest_tweets(self, since_id: str | None = None) -> list[dict]:
        """
        Fetch latest tweets from @Yellow__Korea.
        Returns list of tweet dicts: {id, text, created_at, url, media}
        """
        if self.client:
            return await self._fetch_via_api(since_id)
        return await self._fetch_via_rss(since_id)

    async def _fetch_via_api(self, since_id: str | None = None) -> list[dict]:
        """Fetch tweets using Twitter API v2."""
        tweets = []
        try:
            user_id = await self._get_user_id()
            if not user_id:
                logger.error("Could not resolve user ID")
                return tweets

            params = {
                "max_results": 10,
                "tweet_fields": ["created_at", "text", "attachments"],
                "expansions": ["attachments.media_keys"],
                "media_fields": ["url", "preview_image_url", "type"],
            }
            if since_id:
                params["since_id"] = since_id

            response = self.client.get_users_tweets(user_id, **params)

            if not response or not response.data:
                return tweets

            # Build media lookup
            media_lookup = {}
            if response.includes and "media" in response.includes:
                for media in response.includes["media"]:
                    media_lookup[media.media_key] = {
                        "type": media.type,
                        "url": getattr(media, "url", None)
                        or getattr(media, "preview_image_url", None),
                    }

            for tweet in response.data:
                tweet_url = f"https://x.com/{self.username}/status/{tweet.id}"
                media_urls = []
                if hasattr(tweet, "attachments") and tweet.attachments:
                    media_keys = tweet.attachments.get("media_keys", [])
                    for mk in media_keys:
                        if mk in media_lookup and media_lookup[mk]["url"]:
                            media_urls.append(media_lookup[mk]["url"])

                tweets.append(
                    {
                        "id": str(tweet.id),
                        "text": tweet.text,
                        "created_at": str(tweet.created_at)
                        if tweet.created_at
                        else datetime.now(timezone.utc).isoformat(),
                        "url": tweet_url,
                        "media": media_urls,
                    }
                )

            # Sort oldest first so we process in order
            tweets.sort(key=lambda t: t["id"])

        except Exception as e:
            logger.error(f"Error fetching tweets via API: {e}")

        return tweets

    async def _fetch_via_rss(self, since_id: str | None = None) -> list[dict]:
        """
        Fallback: Fetch tweets via Nitter RSS.
        Uses public Nitter instances for RSS feed.
        """
        tweets = []
        nitter_instances = [
            "nitter.privacydev.net",
            "nitter.poast.org",
        ]

        for instance in nitter_instances:
            try:
                url = f"https://{instance}/{self.username}/rss"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status != 200:
                            continue
                        text = await resp.text()

                from bs4 import BeautifulSoup

                soup = BeautifulSoup(text, "html.parser")
                items = soup.find_all("item")

                for item in items[:10]:
                    title = item.find("title")
                    link = item.find("link")
                    pub_date = item.find("pubdate")
                    description = item.find("description")

                    if not title or not link:
                        continue

                    tweet_text = title.get_text(strip=True)
                    tweet_url = link.get_text(strip=True)

                    # Extract tweet ID from URL
                    tweet_id = tweet_url.rstrip("/").split("/")[-1].replace("#m", "")

                    if since_id and tweet_id <= since_id:
                        continue

                    # Extract media from description
                    media_urls = []
                    if description:
                        desc_soup = BeautifulSoup(
                            description.get_text(), "html.parser"
                        )
                        for img in desc_soup.find_all("img"):
                            src = img.get("src")
                            if src:
                                media_urls.append(src)

                    tweets.append(
                        {
                            "id": tweet_id,
                            "text": tweet_text,
                            "created_at": pub_date.get_text(strip=True)
                            if pub_date
                            else datetime.now(timezone.utc).isoformat(),
                            "url": tweet_url.replace(instance, "x.com"),
                            "media": media_urls,
                        }
                    )

                tweets.sort(key=lambda t: t["id"])
                if tweets:
                    break  # Successfully fetched from this instance

            except Exception as e:
                logger.warning(f"Nitter instance {instance} failed: {e}")
                continue

        return tweets
