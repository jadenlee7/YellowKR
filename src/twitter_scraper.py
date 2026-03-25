"""
Twitter/X scraper for @Yellow__Korea.
Uses Nitter RSS feeds to scrape tweets without API keys.
Multiple Nitter instances as fallback.
"""

import logging
import re
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from src.config import TWITTER_USERNAME, LAST_TWEET_FILE, DATA_DIR

import os

logger = logging.getLogger(__name__)

# Public Nitter instances (updated list, tries multiple)
NITTER_INSTANCES = [
    "nitter.privacydev.net",
    "nitter.poast.org",
    "nitter.woodland.cafe",
    "nitter.kavin.rocks",
    "nitter.1d4.us",
]


def get_last_tweet_id() -> str | None:
    """Read the last processed tweet ID from file."""
    try:
        if os.path.exists(LAST_TWEET_FILE):
            with open(LAST_TWEET_FILE, "r") as f:
                val = f.read().strip()
                return val if val else None
    except Exception as e:
        logger.error(f"Error reading last tweet ID: {e}")
    return None


def save_last_tweet_id(tweet_id: str) -> None:
    """Save the last processed tweet ID to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_TWEET_FILE, "w") as f:
        f.write(str(tweet_id))


class TwitterScraper:
    """Scrapes tweets from @Yellow__Korea via Nitter RSS feeds."""

    def __init__(self):
        self.username = TWITTER_USERNAME

    async def fetch_latest_tweets(self, since_id: str | None = None, limit: int = 10) -> list[dict]:
        """
        Fetch latest tweets via Nitter RSS.
        Returns list of tweet dicts: {id, text, created_at, url}
        """
        for instance in NITTER_INSTANCES:
            tweets = await self._fetch_from_nitter(instance, since_id, limit)
            if tweets:
                return tweets

        # Fallback: try scraping Nitter HTML page
        for instance in NITTER_INSTANCES:
            tweets = await self._fetch_from_nitter_html(instance, since_id, limit)
            if tweets:
                return tweets

        logger.warning("All Nitter instances failed")
        return []

    async def _fetch_from_nitter(
        self, instance: str, since_id: str | None, limit: int
    ) -> list[dict]:
        """Fetch tweets from a specific Nitter instance RSS feed."""
        tweets = []
        url = f"https://{instance}/{self.username}/rss"

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; YellowKRBot/1.0)"
                }
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        logger.debug(f"Nitter {instance} returned {resp.status}")
                        return []
                    text = await resp.text()

            soup = BeautifulSoup(text, "html.parser")
            items = soup.find_all("item")

            for item in items[:limit]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubdate")
                description = item.find("description")

                if not title or not link:
                    continue

                tweet_text = title.get_text(strip=True)
                tweet_url = link.get_text(strip=True) if link.string else str(link.next_sibling).strip()

                # Extract tweet ID from URL
                tweet_id = self._extract_tweet_id(tweet_url)
                if not tweet_id:
                    continue

                if since_id and int(tweet_id) <= int(since_id):
                    continue

                # Clean up tweet URL to use x.com
                clean_url = f"https://x.com/{self.username}/status/{tweet_id}"

                tweets.append({
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": pub_date.get_text(strip=True) if pub_date else datetime.now(timezone.utc).isoformat(),
                    "url": clean_url,
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Fetched {len(tweets)} tweets from Nitter ({instance})")

        except Exception as e:
            logger.debug(f"Nitter RSS {instance} failed: {e}")

        return tweets

    async def _fetch_from_nitter_html(
        self, instance: str, since_id: str | None, limit: int
    ) -> list[dict]:
        """Fallback: scrape Nitter HTML page directly."""
        tweets = []
        url = f"https://{instance}/{self.username}"

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            timeline_items = soup.select(".timeline-item")

            for item in timeline_items[:limit]:
                # Get tweet link
                link_el = item.select_one(".tweet-link")
                if not link_el:
                    continue

                href = link_el.get("href", "")
                tweet_id = self._extract_tweet_id(href)
                if not tweet_id:
                    continue

                if since_id and int(tweet_id) <= int(since_id):
                    continue

                # Get tweet text
                content_el = item.select_one(".tweet-content")
                tweet_text = content_el.get_text(strip=True) if content_el else ""

                # Get timestamp
                time_el = item.select_one(".tweet-date a")
                created_at = time_el.get("title", "") if time_el else datetime.now(timezone.utc).isoformat()

                clean_url = f"https://x.com/{self.username}/status/{tweet_id}"

                tweets.append({
                    "id": tweet_id,
                    "text": tweet_text,
                    "created_at": created_at,
                    "url": clean_url,
                })

            tweets.sort(key=lambda t: int(t["id"]))
            if tweets:
                logger.info(f"Fetched {len(tweets)} tweets from Nitter HTML ({instance})")

        except Exception as e:
            logger.debug(f"Nitter HTML {instance} failed: {e}")

        return tweets

    @staticmethod
    def _extract_tweet_id(url_or_path: str) -> str | None:
        """Extract tweet ID from a Nitter/Twitter URL."""
        match = re.search(r"/status/(\d+)", url_or_path)
        if match:
            return match.group(1)
        # Try just extracting trailing number
        match = re.search(r"(\d{10,})", url_or_path)
        if match:
            return match.group(1)
        return None
