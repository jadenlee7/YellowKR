"""
Telegram Channel Scraper using Telethon.
Monitors @YellowKorea_ann for new posts and forwards them to subscribers.
"""

import logging
import os

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

from src.config import (
    TELEGRAM_API_ID,
    TELEGRAM_API_HASH,
    TELEGRAM_PHONE,
    YELLOW_ANN_CHANNEL,
    LAST_MSG_ID_FILE,
    DATA_DIR,
    SESSION_DIR,
)

logger = logging.getLogger(__name__)


def get_last_msg_id() -> int | None:
    """Read the last processed channel message ID from file."""
    try:
        if os.path.exists(LAST_MSG_ID_FILE):
            with open(LAST_MSG_ID_FILE, "r") as f:
                val = f.read().strip()
                return int(val) if val else None
    except Exception as e:
        logger.error(f"Error reading last message ID: {e}")
    return None


def save_last_msg_id(msg_id: int) -> None:
    """Save the last processed channel message ID to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_MSG_ID_FILE, "w") as f:
        f.write(str(msg_id))


class TelegramChannelScraper:
    """Scrapes messages from @YellowKorea_ann using Telethon."""

    def __init__(self):
        self.channel = YELLOW_ANN_CHANNEL
        self.client: TelegramClient | None = None
        self._initialized = False

    async def init_client(self) -> bool:
        """Initialize the Telethon client."""
        if self._initialized and self.client and self.client.is_connected():
            return True

        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            logger.warning("Telegram API credentials not set. Channel scraping disabled.")
            return False

        try:
            os.makedirs(SESSION_DIR, exist_ok=True)
            session_path = os.path.join(SESSION_DIR, "yellow_scraper")
            self.client = TelegramClient(session_path, TELEGRAM_API_ID, TELEGRAM_API_HASH)
            await self.client.start(phone=TELEGRAM_PHONE if TELEGRAM_PHONE else None)
            self._initialized = True
            logger.info("Telethon client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Telethon client: {e}")
            return False

    async def disconnect(self):
        """Disconnect the Telethon client."""
        if self.client and self.client.is_connected():
            await self.client.disconnect()
            self._initialized = False

    async def fetch_latest_messages(self, since_id: int | None = None, limit: int = 20) -> list[dict]:
        """
        Fetch latest messages from @YellowKorea_ann.
        Returns list of message dicts: {id, text, date, media_type, media_file_id, channel_url}
        """
        if not await self.init_client():
            return []

        messages = []
        try:
            entity = await self.client.get_entity(self.channel)

            async for msg in self.client.iter_messages(entity, limit=limit, min_id=since_id or 0):
                if not msg.text and not msg.media:
                    continue

                media_info = None
                if msg.media:
                    if isinstance(msg.media, MessageMediaPhoto):
                        media_info = {"type": "photo"}
                    elif isinstance(msg.media, MessageMediaDocument):
                        mime = getattr(msg.media.document, "mime_type", "")
                        if "video" in mime:
                            media_info = {"type": "video"}
                        elif "image" in mime or "gif" in mime:
                            media_info = {"type": "animation"}
                        else:
                            media_info = {"type": "document"}

                messages.append({
                    "id": msg.id,
                    "text": msg.text or "",
                    "date": msg.date.isoformat() if msg.date else "",
                    "media": media_info,
                    "raw_message": msg,  # Keep raw for forwarding
                    "channel_url": f"https://t.me/{self.channel}/{msg.id}",
                })

            # Sort oldest first
            messages.sort(key=lambda m: m["id"])

        except Exception as e:
            logger.error(f"Error fetching channel messages: {e}")

        return messages

    async def fetch_recent_posts(self, count: int = 5) -> list[dict]:
        """Fetch the N most recent posts (for /latest command)."""
        if not await self.init_client():
            return []

        messages = []
        try:
            entity = await self.client.get_entity(self.channel)

            async for msg in self.client.iter_messages(entity, limit=count):
                if not msg.text and not msg.media:
                    continue

                messages.append({
                    "id": msg.id,
                    "text": msg.text or "(미디어 포스트)",
                    "date": msg.date.isoformat() if msg.date else "",
                    "channel_url": f"https://t.me/{self.channel}/{msg.id}",
                })

            messages.sort(key=lambda m: m["id"])

        except Exception as e:
            logger.error(f"Error fetching recent posts: {e}")

        return messages
