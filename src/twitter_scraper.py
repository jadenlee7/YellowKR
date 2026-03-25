"""
Twitter/X scraper for @Yellow__Korea.
Uses multiple sources: RSSHub, Nitter instances, Twitter syndication.
"""

import logging
import os
import re
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from src.config import TWITTER_USERNAME, LAST_TWEET_FILE, DATA_DIR

logger = logging.getLogger(__name__)

# RSS sources to try (in order of reliability)
RSS_SOURCES = [
    # RSSHub instances
    "https://rsshub.app/twitter/user/{username}",
    "https://rsshub.rssforever.com/twitter/user/{username}",
    "https://rsshub-instance.zeabur.app/twitter/user/{username}",
    # Nitter instances
    "https://nitter.privacydev.net/{username}/rss",
    "https://nitter.poast.org/{username}/rss",
    "https://nitter.woodland.cafe/{username}/rss",
    "https://nitter.kavin.rocks/{username}/rss",
    "https://nitter.1d4.us/{username}/rss",
]

# Twitter syndication API (no auth needed)
SYNDICATION_URL = "https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"


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
    """Scrapes tweets from @Yellow__Korea via multiple RSS/scraping sources."""

    def __init__(self):
        self.username = TWITTER_USERNAME

    async def fetch_latest_tweets(self, since_id: str | None = None, limit: int = 10) -> list[dict]:
        """Fetch latest tweets. Tries multiple sources until one works."""
        logger.info(f"Fetching tweets for @{self.username}...")

        # Try RSS sources first
        for source_template in RSS_SOURCES:
            source_url = source_template.format(username=self.username)
            tweets = await self._fetch_from_rss(source_url, since_id, limit)
            if tweets:
                return tweets

        # Fallback: Twitter syndication
        tweets = await self._fetch_from_syndication(since_id, limit)
        if tweets:
            return tweets

        logger.warning("All tweet sources failed for @%s", self.username)
        return []

    async def _fetch_from_rss(self, url: str, since_id: str | None, limit: int) -> list[dict]:
        """Fetch tweets from an RSS feed URL."""
        tweets = []
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status != 200:
                        logger.warning(f"RSS source returned {resp.status}: {url}")
                        return []
                    text = await resp.text()

            soup = BeautifulSoup(text, "html.parser")
            items = soup.find_all("item")

            if not items:
                logger.warning(f"No items found in RSS: {url}")
                return []

            for item in items[:limit]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubdate")

                if not title:
                    continue

                tweet_text = title.get_text(strip=True)

                # Get link - handle different RSS formats
                tweet_url = ""
                if link:
                    if link.string:
                        tweet_url = link.get_text(strip=True)
                    elif link.next_sibling:
                        tweet_url = str(link.next_sibling).strip()

                # Try guid as fallback for URL
                if not tweet_url:
                    guid = item.find("guid")
                    if guid:
                        tweet_url = guid.get_text(strip=True)

                # Extract tweet ID
                tweet_id = self._extract_tweet_id(tweet_url or tweet_text)
                if not tweet_id:
                    continue

                if since_id and int(tweet_id) <= int(since_id):
                    continue

                clean_url = f"https://x.com/{self.username}/status/{tweet_id}"

                tweets.append({
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": pub_date.get_text(strip=True) if pub_date else datetime.now(timezone.utc).isoformat(),
                    "url": clean_url,
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Got {len(tweets)} tweets from {url}")

        except Exception as e:
            logger.warning(f"RSS failed [{url}]: {e}")

        return tweets

    async def _fetch_from_syndication(self, since_id: str | None, limit: int) -> list[dict]:
        """Fallback: Twitter syndication API."""
        tweets = []
        url = SYNDICATION_URL.format(username=self.username)

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html",
            }
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"Syndication returned {resp.status}")
                        return []
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")

            # Parse timeline items from syndication HTML
            for article in soup.select("[data-tweet-id]")[:limit]:
                tweet_id = article.get("data-tweet-id", "")
                if not tweet_id:
                    continue

                if since_id and int(tweet_id) <= int(since_id):
                    continue

                # Get tweet text
                text_el = article.select_one(".timeline-Tweet-text")
                tweet_text = text_el.get_text(strip=True) if text_el else ""

                clean_url = f"https://x.com/{self.username}/status/{tweet_id}"

                tweets.append({
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "url": clean_url,
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Got {len(tweets)} tweets from syndication")

        except Exception as e:
            logger.warning(f"Syndication failed: {e}")

        return tweets

    @staticmethod
    def _extract_tweet_id(url_or_text: str) -> str | None:
        """Extract tweet ID from a URL or text."""
        match = re.search(r"/status/(\d+)", url_or_text)
        if match:
            return match.group(1)
        match = re.search(r"(\d{15,})", url_or_text)
        if match:
            return match.group(1)
        return None
