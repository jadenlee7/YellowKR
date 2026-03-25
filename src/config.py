import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram Bot ──
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@YellowKorea_chat")

# ── Twitter/X ──
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "Yellow__Korea")

# ── Anthropic Claude API ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Intervals (minutes) ──
TWITTER_SCRAPE_INTERVAL_MINUTES = int(os.getenv("TWITTER_SCRAPE_INTERVAL_MINUTES", "5"))
AUTO_TIP_INTERVAL_MINUTES = int(os.getenv("AUTO_TIP_INTERVAL_MINUTES", "60"))

# ── Data paths ──
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAST_TWEET_FILE = os.path.join(DATA_DIR, "last_tweet_id.txt")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
