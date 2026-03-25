"""
Yellow Korea Telegram Bot.
Scrapes @Yellow__Korea Twitter + AI chat with users.
All messages use HTML parse mode for proper bold/italic rendering.
"""

import logging
import re
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

from src.config import (
    TELEGRAM_BOT_TOKEN,
    TWITTER_SCRAPE_INTERVAL_MINUTES,
    AUTO_TIP_INTERVAL_MINUTES,
)
from src.yellow_knowledge import YellowChatHandler, YELLOW_INFO, get_random_tip
from src.subscribers import SubscriberManager
from src.twitter_scraper import (
    TwitterScraper,
    get_last_tweet_id,
    save_last_tweet_id,
)

logger = logging.getLogger(__name__)

chat_handler = YellowChatHandler()
subscriber_manager = SubscriberManager()
twitter_scraper = TwitterScraper()


def md_to_html(text: str) -> str:
    """Convert markdown bold/italic to HTML and escape bare HTML chars."""
    # Escape HTML special chars first (but not existing tags)
    # Replace **bold** with <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Replace *italic* with <i>italic</i>
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def escape_html(text: str) -> str:
    """Escape HTML special characters for safe Telegram HTML."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_name = escape_html(user.first_name) if user else "유저"

    welcome_text = (
        f"안녕하세요 {user_name}님!\n"
        f"<b>Yellow Korea Bot</b>에 오신 것을 환영합니다!\n\n"
        f"이 봇은 @Yellow__Korea 트윗을 실시간으로 전달하고,\n"
        f"Yellow Network에 대한 정보를 AI로 제공합니다.\n\n"
        f"<b>주요 기능:</b>\n"
        f"- @Yellow__Korea 트윗 실시간 알림\n"
        f"- Yellow Network 정보 제공 (Claude AI)\n"
        f"- 정기적인 Yellow 팁\n\n"
        f"/subscribe 를 눌러 알림을 구독하세요!"
    )

    keyboard = [
        [
            InlineKeyboardButton("공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("채팅방", url="https://t.me/YellowKorea_chat"),
        ],
        [
            InlineKeyboardButton("Twitter/X", url="https://x.com/Yellow__Korea"),
            InlineKeyboardButton("Yellow.org", url="https://www.yellow.org"),
        ],
        [
            InlineKeyboardButton("알림 구독하기", callback_data="subscribe"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )

    chat_id = update.effective_chat.id
    if subscriber_manager.add(chat_id):
        await update.message.reply_text(
            "자동으로 알림이 구독되었습니다!\n"
            "새 트윗이 올라오면 바로 알려드릴게요.\n"
            "해제: /unsubscribe"
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "<b>사용 가능한 명령어:</b>\n\n"
        "/start - 봇 시작 &amp; 소개\n"
        "/about - Yellow Network 소개\n"
        "/links - 공식 링크 모음\n"
        "/subscribe - 트윗 알림 구독\n"
        "/unsubscribe - 트윗 알림 해제\n"
        "/latest - 최근 트윗 보기\n"
        "/tip - Yellow 팁 받기\n"
        "/help - 도움말\n\n"
        "자유롭게 Yellow에 대해 질문해주세요!\n"
        "AI가 친절하게 답변해드립니다."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"<b>Yellow Network 소개</b>\n\n"
        f"{YELLOW_INFO['about']}\n\n"
        f"<b>주요 기능:</b>\n{YELLOW_INFO['features']}\n\n"
        f"<b>토큰:</b>\n{YELLOW_INFO['token']}\n\n"
        f"<b>최신 업데이트:</b>\n"
        f"https://x.com/Yellow__Korea"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("채팅방", url="https://t.me/YellowKorea_chat"),
        ],
        [
            InlineKeyboardButton("Twitter/X", url="https://x.com/Yellow__Korea"),
            InlineKeyboardButton("Yellow.org", url="https://www.yellow.org"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "<b>공식 채널:</b>\n"
        "- Twitter/X: https://x.com/Yellow__Korea\n"
        "- Telegram 공지방: https://t.me/YellowKorea_ann\n"
        "- Telegram 채팅방: https://t.me/YellowKorea_chat\n"
        "- Yellow Network: https://www.yellow.org"
    )
    await update.message.reply_text(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if subscriber_manager.add(chat_id):
        await update.message.reply_text(
            "트윗 알림을 구독했습니다!\n"
            "@Yellow__Korea 새 트윗이 올라오면 바로 알려드릴게요."
        )
    else:
        await update.message.reply_text("이미 알림을 구독 중입니다!")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if subscriber_manager.remove(chat_id):
        await update.message.reply_text("알림 구독을 해제했습니다.\n다시 구독: /subscribe")
    else:
        await update.message.reply_text("현재 알림을 구독하고 있지 않습니다.")


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("@Yellow__Korea 최근 트윗을 가져오는 중...")

    try:
        tweets = await twitter_scraper.fetch_latest_tweets(limit=5)
        if not tweets:
            await update.message.reply_text(
                "최근 트윗을 가져올 수 없습니다.\n"
                "직접 확인: https://x.com/Yellow__Korea"
            )
            return

        for tweet in tweets[-5:]:
            text = format_tweet_message(tweet)
            await update.message.reply_text(
                text, disable_web_page_preview=False, parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Error fetching tweets: {e}")
        await update.message.reply_text(
            "트윗을 가져오는 중 오류가 발생했습니다.\n"
            "직접 확인: https://x.com/Yellow__Korea"
        )


async def cmd_tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tip = get_random_tip()
    await update.message.reply_text(tip, parse_mode=ParseMode.HTML)


# ──────────────────────────────────────────────
# Callback / Message Handlers
# ──────────────────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    user = update.effective_user
    user_name = user.first_name if user else ""

    response = await chat_handler.get_response(user_message, user_name=user_name)
    # Convert any remaining markdown bold to HTML
    response = md_to_html(response)

    try:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception:
        # Fallback: send without parse mode if HTML is malformed
        await update.message.reply_text(response)


# ──────────────────────────────────────────────
# Tweet Broadcasting
# ──────────────────────────────────────────────


def format_tweet_message(tweet: dict) -> str:
    preview = escape_html(tweet["text"])
    if len(preview) > 500:
        preview = preview[:500] + "..."

    return (
        f"<b>@Yellow__Korea 새 트윗</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Link: {tweet['url']}"
    )


async def check_and_broadcast_tweets(context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Checking for new tweets from @Yellow__Korea...")

    since_id = get_last_tweet_id()
    tweets = await twitter_scraper.fetch_latest_tweets(since_id=since_id)

    if not tweets:
        logger.info("No new tweets")
        return

    subscribers = subscriber_manager.get_all()
    logger.info(f"Found {len(tweets)} new tweets → {len(subscribers)} subscribers")

    for tweet in tweets:
        text = format_tweet_message(tweet)

        for chat_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    disable_web_page_preview=False,
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
                if "Forbidden" in str(e) or "blocked" in str(e).lower():
                    subscriber_manager.remove(chat_id)

        save_last_tweet_id(tweet["id"])

    logger.info("Tweet broadcast complete")


async def send_periodic_tip(context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribers = subscriber_manager.get_all()
    if not subscribers:
        return

    tip = get_random_tip()
    logger.info(f"Sending periodic tip → {len(subscribers)} subscribers")

    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=tip, parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Failed to send tip to {chat_id}: {e}")
            if "Forbidden" in str(e) or "blocked" in str(e).lower():
                subscriber_manager.remove(chat_id)


# ──────────────────────────────────────────────
# Bot Setup
# ──────────────────────────────────────────────


def create_bot() -> Application:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set!")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("links", cmd_links))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))
    app.add_handler(CommandHandler("unsubscribe", cmd_unsubscribe))
    app.add_handler(CommandHandler("latest", cmd_latest))
    app.add_handler(CommandHandler("tip", cmd_tip))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_and_broadcast_tweets,
            interval=TWITTER_SCRAPE_INTERVAL_MINUTES * 60,
            first=15,
            name="tweet_checker",
        )
        logger.info(f"Tweet checker: every {TWITTER_SCRAPE_INTERVAL_MINUTES} min")

        job_queue.run_repeating(
            send_periodic_tip,
            interval=AUTO_TIP_INTERVAL_MINUTES * 60,
            first=AUTO_TIP_INTERVAL_MINUTES * 60,
            name="auto_tip",
        )
        logger.info(f"Auto-tip: every {AUTO_TIP_INTERVAL_MINUTES} min")

    return app
