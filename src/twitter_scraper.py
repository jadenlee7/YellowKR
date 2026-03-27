"""
Twitter/X scraper for @Yellow__Korea.
Primary: Twitter API v2 (Bearer Token) - most reliable.
Fallback: RSS bridges, Nitter, syndication.
"""

import logging
import os
import re
import json
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from src.config import TWITTER_USERNAME, LAST_TWEET_FILE, DATA_DIR

logger = logging.getLogger(__name__)

# Twitter API v2 Bearer Token (set in env)
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")

# Fallback RSS sources
RSS_SOURCES = [
    "https://rsshub.app/twitter/user/{username}",
    "https://rsshub.rssforever.com/twitter/user/{username}",
    "https://nitter.privacydev.net/{username}/rss",
    "https://nitter.poast.org/{username}/rss",
]


def get_last_tweet_id() -> str | None:
    try:
        if os.path.exists(LAST_TWEET_FILE):
            with open(LAST_TWEET_FILE, "r") as f:
                val = f.read().strip()
                return val if val else None
    except Exception as e:
        logger.error(f"Error reading last tweet ID: {e}")
    return None


def save_last_tweet_id(tweet_id: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_TWEET_FILE, "w") as f:
        f.write(str(tweet_id))


class TwitterScraper:
    """Scrapes tweets from a Twitter account. Uses Twitter API v2 if available."""

    def __init__(self, username_override: str | None = None):
        self.username = username_override or TWITTER_USERNAME
        self._user_id: str | None = None

    async def fetch_latest_tweets(self, since_id: str | None = None, limit: int = 10) -> list[dict]:
        """Fetch latest tweets. Tries API first, then fallbacks."""
        logger.info(f"Fetching tweets for @{self.username}...")

        # 1. Twitter API v2 (most reliable)
        if TWITTER_BEARER_TOKEN:
            tweets = await self._fetch_via_api(since_id, limit)
            if tweets:
                return tweets
            logger.warning("Twitter API v2 failed, trying fallbacks...")

        # 2. FxTwitter API (no auth needed)
        tweets = await self._fetch_via_fxtwitter(since_id, limit)
        if tweets:
            return tweets

        # 3. RSS fallbacks
        for source_template in RSS_SOURCES:
            source_url = source_template.format(username=self.username)
            tweets = await self._fetch_from_rss(source_url, since_id, limit)
            if tweets:
                return tweets

        logger.warning("All tweet sources failed for @%s", self.username)
        return []

    # ── Twitter API v2 ──

    async def _get_user_id(self) -> str | None:
        """Get Twitter user ID from username via API v2."""
        if self._user_id:
            return self._user_id

        url = f"https://api.twitter.com/2/users/by/username/{self.username}"
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"Twitter user lookup returned {resp.status}")
                        return None
                    data = await resp.json()
                    self._user_id = data.get("data", {}).get("id")
                    return self._user_id
        except Exception as e:
            logger.warning(f"Twitter user lookup failed: {e}")
            return None

    async def _fetch_via_api(self, since_id: str | None, limit: int) -> list[dict]:
        """Fetch tweets using Twitter API v2."""
        user_id = await self._get_user_id()
        if not user_id:
            return []

        url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
        params = {
            "max_results": min(limit, 100),
            "tweet.fields": "created_at,text",
        }
        if since_id:
            params["since_id"] = since_id

        tweets = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(f"Twitter API returned {resp.status}: {body[:200]}")
                        return []
                    data = await resp.json()

            for tweet in data.get("data", []):
                tweet_id = tweet["id"]
                tweets.append({
                    "id": tweet_id,
                    "text": tweet["text"],
                    "created_at": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "url": f"https://x.com/{self.username}/status/{tweet_id}",
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Got {len(tweets)} tweets from Twitter API v2")

        except Exception as e:
            logger.warning(f"Twitter API failed: {e}")

        return tweets

    # ── FxTwitter API (no auth) ──

    async def _fetch_via_fxtwitter(self, since_id: str | None, limit: int) -> list[dict]:
        """Fetch tweets via FxTwitter/FixTweet API (no auth needed)."""
        tweets = []
        url = f"https://api.fxtwitter.com/{self.username}"

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {"User-Agent": "YellowKRBot/1.0"}
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"FxTwitter returned {resp.status}")
                        return []
                    data = await resp.json()

            for tweet in data.get("tweets", [])[:limit]:
                tweet_id = str(tweet.get("id", ""))
                if not tweet_id:
                    continue

                if since_id and int(tweet_id) <= int(since_id):
                    continue

                tweets.append({
                    "id": tweet_id,
                    "text": tweet.get("text", ""),
                    "created_at": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "url": tweet.get("url", f"https://x.com/{self.username}/status/{tweet_id}"),
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Got {len(tweets)} tweets from FxTwitter")

        except Exception as e:
            logger.warning(f"FxTwitter failed: {e}")

        return tweets

    # ── RSS Fallback ──

    async def _fetch_from_rss(self, url: str, since_id: str | None, limit: int) -> list[dict]:
        """Fetch tweets from an RSS feed URL."""
        tweets = []
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status != 200:
                        logger.warning(f"RSS returned {resp.status}: {url}")
                        return []
                    text = await resp.text()

            soup = BeautifulSoup(text, "html.parser")
            items = soup.find_all("item")

            if not items:
                return []

            for item in items[:limit]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubdate")

                if not title:
                    continue

                tweet_text = title.get_text(strip=True)
                tweet_url = ""
                if link:
                    tweet_url = link.get_text(strip=True) if link.string else str(link.next_sibling).strip()
                if not tweet_url:
                    guid = item.find("guid")
                    if guid:
                        tweet_url = guid.get_text(strip=True)

                tweet_id = self._extract_tweet_id(tweet_url or tweet_text)
                if not tweet_id:
                    continue
                if since_id and int(tweet_id) <= int(since_id):
                    continue

                tweets.append({
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": pub_date.get_text(strip=True) if pub_date else datetime.now(timezone.utc).isoformat(),
                    "url": f"https://x.com/{self.username}/status/{tweet_id}",
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Got {len(tweets)} tweets from RSS: {url}")

        except Exception as e:
            logger.warning(f"RSS failed [{url}]: {e}")

        return tweets

    @staticmethod
    def _extract_tweet_id(url_or_text: str) -> str | None:
        match = re.search(r"/status/(\d+)", url_or_text)
        if match:
            return match.group(1)
        match = re.search(r"(\d{15,})", url_or_text)
        if match:
            return match.group(1)
        return None
