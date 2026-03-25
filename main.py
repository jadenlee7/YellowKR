"""
Yellow Korea Bot - Main Entry Point

A Telegram bot that:
1. Scrapes @Yellow__Korea tweets and broadcasts to subscribers
2. Provides Yellow Network information
3. Chats with users about Yellow
4. References Yellow Korea announcement channel (https://t.me/YellowKorea_ann)
"""

import logging
import os
import sys

from src.config import SCRAPE_INTERVAL_MINUTES, DATA_DIR
from src.bot import create_bot, check_and_broadcast_tweets

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

    # Create bot application
    app = create_bot()

    # Schedule tweet checking job
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_and_broadcast_tweets,
            interval=SCRAPE_INTERVAL_MINUTES * 60,
            first=10,  # First check 10 seconds after start
            name="tweet_checker",
        )
        logger.info(
            f"Tweet checker scheduled every {SCRAPE_INTERVAL_MINUTES} minutes"
        )
    else:
        logger.warning("Job queue not available. Tweet broadcasting disabled.")

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
