import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Twitter/X
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "Yellow__Korea")

# OpenAI (optional, for AI chat)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Yellow Korea Announcement Channel
YELLOW_ANN_CHANNEL = os.getenv("YELLOW_ANN_CHANNEL", "@YellowKorea_ann")

# Scrape interval
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "5"))

# Bot language
BOT_LANGUAGE = os.getenv("BOT_LANGUAGE", "ko")

# Data paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAST_TWEET_FILE = os.path.join(DATA_DIR, "last_tweet_id.txt")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
