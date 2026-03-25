import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram Bot (python-telegram-bot) ──
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ── Telegram Userbot / Scraper (Telethon) ──
# Get these from https://my.telegram.org/apps
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")  # Phone number for Telethon session

# ── Source Channel to Monitor ──
YELLOW_ANN_CHANNEL = os.getenv("YELLOW_ANN_CHANNEL", "YellowKorea_ann")

# ── OpenAI (optional, for AI chat) ──
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Scrape / Check Interval ──
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "3"))

# ── Auto-engagement settings ──
# Periodic Yellow tips interval (in minutes)
AUTO_TIP_INTERVAL_MINUTES = int(os.getenv("AUTO_TIP_INTERVAL_MINUTES", "60"))
# Welcome message delay (seconds after new user starts bot)
WELCOME_DELAY_SECONDS = int(os.getenv("WELCOME_DELAY_SECONDS", "2"))

# ── Data paths ──
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAST_MSG_ID_FILE = os.path.join(DATA_DIR, "last_channel_msg_id.txt")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
SESSION_DIR = os.path.join(DATA_DIR, "sessions")
