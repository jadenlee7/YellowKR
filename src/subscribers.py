"""
Subscriber management for tweet notifications.
"""

import json
import logging
import os

from src.config import SUBSCRIBERS_FILE, DATA_DIR

logger = logging.getLogger(__name__)


def load_subscribers() -> set[int]:
    """Load subscriber chat IDs from file."""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, "r") as f:
                data = json.load(f)
                return set(data.get("subscribers", []))
    except Exception as e:
        logger.error(f"Error loading subscribers: {e}")
    return set()


def save_subscribers(subscribers: set[int]) -> None:
    """Save subscriber chat IDs to file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump({"subscribers": list(subscribers)}, f)


class SubscriberManager:
    """Manages tweet notification subscribers."""

    def __init__(self):
        self.subscribers = load_subscribers()

    def add(self, chat_id: int) -> bool:
        """Add a subscriber. Returns True if newly added."""
        if chat_id in self.subscribers:
            return False
        self.subscribers.add(chat_id)
        save_subscribers(self.subscribers)
        return True

    def remove(self, chat_id: int) -> bool:
        """Remove a subscriber. Returns True if was subscribed."""
        if chat_id not in self.subscribers:
            return False
        self.subscribers.discard(chat_id)
        save_subscribers(self.subscribers)
        return True

    def get_all(self) -> set[int]:
        """Get all subscriber chat IDs."""
        return self.subscribers.copy()

    def count(self) -> int:
        """Get subscriber count."""
        return len(self.subscribers)
