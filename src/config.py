import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram Bot (python-telegram-bot) ──
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Telegram Chat Group (where bot operates) ──
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@YellowKorea_chat")

# ── Telegram Userbot / Scraper (Telethon) ──
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")

# ── Source Channel to Monitor ──
YELLOW_ANN_CHANNEL = os.getenv("YELLOW_ANN_CHANNEL", "YellowKorea_ann")

# ── Twitter/X account to scrape ──
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "Yellow__Korea")

# ── Anthropic Claude API ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Intervals ──
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "3"))
TWITTER_SCRAPE_INTERVAL_MINUTES = int(os.getenv("TWITTER_SCRAPE_INTERVAL_MINUTES", "5"))
AUTO_TIP_INTERVAL_MINUTES = int(os.getenv("AUTO_TIP_INTERVAL_MINUTES", "60"))

# ── Data paths ──
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAST_MSG_ID_FILE = os.path.join(DATA_DIR, "last_channel_msg_id.txt")
LAST_TWEET_FILE = os.path.join(DATA_DIR, "last_tweet_id.txt")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
SESSION_DIR = os.path.join(DATA_DIR, "sessions")
