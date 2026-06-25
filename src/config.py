import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram Bot ──
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "@YellowKorea_chat")

# Owner's numeric Telegram user ID. Daily summary reports are DM'd here.
# Get it by sending /myid to the bot in a private chat.
OWNER_TELEGRAM_ID = os.getenv("OWNER_TELEGRAM_ID", "")

# ── Twitter/X ──
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME", "Yellow__Korea")
TWITTER_MAIN_USERNAME = os.getenv("TWITTER_MAIN_USERNAME", "yellow")

# ── Anthropic Claude API ──
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Intervals (minutes) ──
TWITTER_SCRAPE_INTERVAL_MINUTES = int(os.getenv("TWITTER_SCRAPE_INTERVAL_MINUTES", "5"))
# Auto-post is checked this often, but only actually posts when the chat has
# been active and the bot wasn't the last to speak (see auto-post gating below).
# Default 240 min (4h) ≈ 2-3 posts/day within posting hours.
AUTO_POST_INTERVAL_MINUTES = int(os.getenv("AUTO_POST_INTERVAL_MINUTES", "240"))

# ── Auto-post gating (keeps the bot from talking to itself) ──
# Minimum number of human messages since the bot's last auto-post before it may
# post again. Prevents cluttering a quiet room.
MIN_HUMAN_MSGS_BEFORE_POST = int(os.getenv("MIN_HUMAN_MSGS_BEFORE_POST", "8"))
# Hard cap on auto-posts per day regardless of activity.
MAX_AUTO_POSTS_PER_DAY = int(os.getenv("MAX_AUTO_POSTS_PER_DAY", "3"))

# ── Moderation / anti-spam ──
# "delete" = delete + warn + mute repeat offenders, "report" = only log to the
# daily report (no deletion), "off" = disabled.
SPAM_ACTION = os.getenv("SPAM_ACTION", "delete").lower()
# Number of spam offenses before a user is temporarily muted.
SPAM_MUTE_THRESHOLD = int(os.getenv("SPAM_MUTE_THRESHOLD", "3"))
# Mute duration in minutes.
SPAM_MUTE_MINUTES = int(os.getenv("SPAM_MUTE_MINUTES", "60"))

# ── Daily report ──
# Hour (KST, 0-23) to DM the owner the daily summary.
DAILY_REPORT_HOUR_KST = int(os.getenv("DAILY_REPORT_HOUR_KST", "9"))

# ── Data paths ──
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAST_TWEET_FILE = os.path.join(DATA_DIR, "last_tweet_id.txt")
LAST_MAIN_TWEET_FILE = os.path.join(DATA_DIR, "last_main_tweet_id.txt")
SUBSCRIBERS_FILE = os.path.join(DATA_DIR, "subscribers.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
