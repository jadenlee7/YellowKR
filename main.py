"""
Yellow Korea Bot - Main Entry Point

A Telegram bot that:
1. Scrapes @YellowKorea_ann channel posts and broadcasts to subscribers
2. Provides Yellow Network information via chat
3. Auto-engages users with periodic Yellow tips
4. References Yellow Korea announcement channel and @Yellow__Korea Twitter
"""

import logging
import os
import sys

from src.config import DATA_DIR
from src.bot import create_bot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Start the Yellow Korea bot."""
    logger.info("Starting Yellow Korea Bot...")

    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Create and run bot (jobs are scheduled inside create_bot)
    app = create_bot()

    logger.info("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
