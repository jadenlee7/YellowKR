"""
Yellow Korea Bot - Main Entry Point
Scrapes @Yellow__Korea Twitter + AI chat with users.
"""

import logging
import os
import sys

# Force unbuffered output for Railway
os.environ["PYTHONUNBUFFERED"] = "1"

from src.config import DATA_DIR
from src.bot import create_bot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    print("=== Yellow Korea Bot Starting ===", flush=True)
    logger.info("Starting Yellow Korea Bot...")

    os.makedirs(DATA_DIR, exist_ok=True)

    app = create_bot()

    # Verify job queue
    if app.job_queue:
        jobs = app.job_queue.jobs()
        print(f"=== Job Queue OK: {len(jobs)} jobs scheduled ===", flush=True)
        for job in jobs:
            print(f"  - {job.name}", flush=True)
    else:
        print("=== WARNING: Job Queue is None! Tweet scraping DISABLED ===", flush=True)

    print("=== Bot polling started ===", flush=True)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
