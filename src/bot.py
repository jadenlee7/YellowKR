"""
Yellow Korea Telegram Bot.
Delivers @Yellow__Korea tweets and answers questions about Yellow Network.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

from src.config import TELEGRAM_BOT_TOKEN, YELLOW_ANN_CHANNEL
from src.yellow_knowledge import YellowChatHandler, YELLOW_INFO
from src.subscribers import SubscriberManager
from src.twitter_scraper import TwitterScraper, get_last_tweet_id, save_last_tweet_id

logger = logging.getLogger(__name__)

# Global instances
chat_handler = YellowChatHandler()
subscriber_manager = SubscriberManager()
twitter_scraper = TwitterScraper()


def escape_md(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    special_chars = r"_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_text = (
        "Yellow Korea Bot에 오신 것을 환영합니다!\n\n"
        "이 봇은 Yellow Network의 최신 소식을 전달하고,\n"
        "Yellow에 대한 정보를 제공합니다.\n\n"
        "주요 기능:\n"
        "- @Yellow__Korea 트윗 실시간 알림\n"
        "- Yellow Network 정보 제공\n"
        "- Yellow 관련 질문 답변\n\n"
        "명령어 목록은 /help 를 입력하세요!"
    )

    keyboard = [
        [
            InlineKeyboardButton("Yellow Korea 공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("Twitter/X", url="https://x.com/Yellow__Korea"),
        ],
        [
            InlineKeyboardButton("트윗 알림 구독", callback_data="subscribe"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "사용 가능한 명령어:\n\n"
        "/start - 봇 시작 & 소개\n"
        "/about - Yellow Network 소개\n"
        "/links - 공식 링크 모음\n"
        "/subscribe - 트윗 알림 구독\n"
        "/unsubscribe - 트윗 알림 해제\n"
        "/latest - 최근 트윗 보기\n"
        "/help - 도움말\n\n"
        "또는 자유롭게 Yellow에 대해 질문해주세요!"
    )
    await update.message.reply_text(help_text)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    text = f"{YELLOW_INFO['about']}\n\n{YELLOW_INFO['features']}"
    await update.message.reply_text(text)


async def cmd_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /links command."""
    keyboard = [
        [
            InlineKeyboardButton("Yellow Korea 공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("Twitter/X", url="https://x.com/Yellow__Korea"),
        ],
        [
            InlineKeyboardButton("Yellow Network", url="https://www.yellow.org"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(YELLOW_INFO["links"], reply_markup=reply_markup)


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /subscribe command."""
    chat_id = update.effective_chat.id
    if subscriber_manager.add(chat_id):
        await update.message.reply_text(
            "트윗 알림을 구독했습니다!\n"
            "@Yellow__Korea의 새 트윗이 올라오면 알려드릴게요."
        )
    else:
        await update.message.reply_text("이미 트윗 알림을 구독 중입니다!")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unsubscribe command."""
    chat_id = update.effective_chat.id
    if subscriber_manager.remove(chat_id):
        await update.message.reply_text("트윗 알림 구독을 해제했습니다.")
    else:
        await update.message.reply_text("현재 트윗 알림을 구독하고 있지 않습니다.")


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /latest command - show recent tweets."""
    await update.message.reply_text("최근 트윗을 가져오는 중...")

    try:
        tweets = await twitter_scraper.fetch_latest_tweets()
        if not tweets:
            await update.message.reply_text(
                "최근 트윗을 가져올 수 없습니다.\n"
                "직접 확인해주세요: https://x.com/Yellow__Korea"
            )
            return

        # Show up to 5 most recent tweets
        for tweet in tweets[-5:]:
            text = format_tweet_message(tweet)
            await update.message.reply_text(text, disable_web_page_preview=False)

    except Exception as e:
        logger.error(f"Error fetching latest tweets: {e}")
        await update.message.reply_text(
            "트윗을 가져오는 중 오류가 발생했습니다.\n"
            "직접 확인해주세요: https://x.com/Yellow__Korea"
        )


# ──────────────────────────────────────────────
# Callback Query Handler
# ──────────────────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == "subscribe":
        chat_id = update.effective_chat.id
        if subscriber_manager.add(chat_id):
            await query.edit_message_text(
                query.message.text + "\n\n트윗 알림을 구독했습니다!"
            )
        else:
            await query.answer("이미 구독 중입니다!", show_alert=True)


# ──────────────────────────────────────────────
# Message Handler (Chat)
# ──────────────────────────────────────────────


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages - chat about Yellow."""
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    response = await chat_handler.get_response(user_message)
    await update.message.reply_text(response)


# ──────────────────────────────────────────────
# Tweet Broadcasting
# ──────────────────────────────────────────────


def format_tweet_message(tweet: dict) -> str:
    """Format a tweet into a Telegram message."""
    text = (
        f"@Yellow__Korea 새 트윗\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{tweet['text']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Link: {tweet['url']}"
    )
    return text


async def check_and_broadcast_tweets(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: check for new tweets and broadcast to subscribers."""
    logger.info("Checking for new tweets...")

    since_id = get_last_tweet_id()
    tweets = await twitter_scraper.fetch_latest_tweets(since_id=since_id)

    if not tweets:
        logger.info("No new tweets found")
        return

    subscribers = subscriber_manager.get_all()
    logger.info(f"Found {len(tweets)} new tweets, broadcasting to {len(subscribers)} subscribers")

    for tweet in tweets:
        message = format_tweet_message(tweet)

        for chat_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    disable_web_page_preview=False,
                )
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
                # Remove subscribers who blocked the bot
                if "Forbidden" in str(e) or "blocked" in str(e).lower():
                    subscriber_manager.remove(chat_id)

        # Save last tweet ID
        save_last_tweet_id(tweet["id"])

    logger.info("Tweet broadcast complete")


# ──────────────────────────────────────────────
# Bot Setup
# ──────────────────────────────────────────────


def create_bot() -> Application:
    """Create and configure the Telegram bot application."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("links", cmd_links))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("latest", cmd_latest))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    return app
