"""
Yellow Korea Telegram Bot.
Scrapes @Yellow__Korea + @yellow Twitter, AI chat, auto-engagement posts.
"""

import logging
import re
from datetime import datetime, timezone, timedelta
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
    TELEGRAM_CHAT_ID,
    TWITTER_SCRAPE_INTERVAL_MINUTES,
    AUTO_POST_INTERVAL_MINUTES,
    TWITTER_MAIN_USERNAME,
)
from src.yellow_knowledge import YellowChatHandler, YELLOW_INFO
from src.subscribers import SubscriberManager
from src.twitter_scraper import (
    TwitterScraper,
    get_last_tweet_id,
    save_last_tweet_id,
)
from src.auto_post import (
    is_within_posting_hours,
    is_yellow_pro_content,
    get_last_main_tweet_id,
    save_last_main_tweet_id,
    get_engagement_post,
    generate_tweet_discussion,
    format_yellow_main_tweet,
)
from src.spam_filter import should_ignore as should_ignore_message

logger = logging.getLogger(__name__)

chat_handler = YellowChatHandler()
subscriber_manager = SubscriberManager()
twitter_scraper = TwitterScraper()
# Separate scraper for @yellow main account
yellow_main_scraper = TwitterScraper(username_override=TWITTER_MAIN_USERNAME)


def md_to_html(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    return text


def escape_html(text: str) -> str:
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
        f"이 봇은 @Yellow__Korea, @yellow 트윗을 실시간으로 전달하고,\n"
        f"Yellow Network에 대한 정보를 AI로 제공합니다.\n\n"
        f"<b>주요 기능:</b>\n"
        f"- @yellow + @Yellow__Korea 트윗 실시간 알림\n"
        f"- 크립토 뉴스 &amp; 토론 자동 포스팅\n"
        f"- Yellow Network 정보 제공 (Claude AI)\n\n"
        f"/subscribe 를 눌러 알림을 구독하세요!"
    )

    keyboard = [
        [
            InlineKeyboardButton("공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("채팅방", url="https://t.me/YellowKorea_chat"),
        ],
        [
            InlineKeyboardButton("@yellow", url="https://x.com/yellow"),
            InlineKeyboardButton("@Yellow__Korea", url="https://x.com/Yellow__Korea"),
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
        f"https://x.com/yellow"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("공지방", url="https://t.me/YellowKorea_ann"),
            InlineKeyboardButton("채팅방", url="https://t.me/YellowKorea_chat"),
        ],
        [
            InlineKeyboardButton("@yellow", url="https://x.com/yellow"),
            InlineKeyboardButton("@Yellow__Korea", url="https://x.com/Yellow__Korea"),
        ],
        [
            InlineKeyboardButton("Yellow.org", url="https://www.yellow.org"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "<b>공식 채널:</b>\n"
        "- Twitter (Global): https://x.com/yellow\n"
        "- Twitter (Korea): https://x.com/Yellow__Korea\n"
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
            "@yellow + @Yellow__Korea 새 트윗이 올라오면 바로 알려드릴게요."
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
    await update.message.reply_text("최근 트윗을 가져오는 중...")

    sent_any = False
    # @yellow main
    try:
        tweets = await yellow_main_scraper.fetch_latest_tweets(limit=3)
        for tweet in tweets[-3:]:
            if not is_yellow_pro_content(tweet["text"]):
                text = format_yellow_main_tweet(tweet)
                await update.message.reply_text(
                    text, disable_web_page_preview=False, parse_mode=ParseMode.HTML
                )
                sent_any = True
    except Exception as e:
        logger.error(f"Error fetching @yellow tweets: {e}")

    # @Yellow__Korea
    try:
        tweets = await twitter_scraper.fetch_latest_tweets(limit=3)
        for tweet in tweets[-3:]:
            text = format_korea_tweet(tweet)
            await update.message.reply_text(
                text, disable_web_page_preview=False, parse_mode=ParseMode.HTML
            )
            sent_any = True
    except Exception as e:
        logger.error(f"Error fetching @Yellow__Korea tweets: {e}")

    if not sent_any:
        await update.message.reply_text(
            "최근 트윗을 가져올 수 없습니다.\n"
            "직접 확인: https://x.com/yellow"
        )


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

    if should_ignore_message(update.message):
        return

    user_message = update.message.text
    user = update.effective_user
    user_name = user.first_name if user else ""

    response = await chat_handler.get_response(user_message, user_name=user_name)
    response = md_to_html(response)

    try:
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception:
        await update.message.reply_text(response)


# ──────────────────────────────────────────────
# Tweet Formatting
# ──────────────────────────────────────────────


def format_korea_tweet(tweet: dict) -> str:
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


# ──────────────────────────────────────────────
# Scheduled Jobs
# ──────────────────────────────────────────────


async def check_korea_tweets(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check @Yellow__Korea for new tweets."""
    logger.info("Checking @Yellow__Korea tweets...")
    since_id = get_last_tweet_id()
    tweets = await twitter_scraper.fetch_latest_tweets(since_id=since_id)

    if not tweets:
        logger.info("No new @Yellow__Korea tweets")
        return

    subscribers = subscriber_manager.get_all()
    for tweet in tweets:
        text = format_korea_tweet(tweet)
        await _broadcast(context, subscribers, text)
        save_last_tweet_id(tweet["id"])


async def check_yellow_main_tweets(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check @yellow for new tweets (filter out Yellow Pro)."""
    logger.info("Checking @yellow main tweets...")
    since_id = get_last_main_tweet_id()
    tweets = await yellow_main_scraper.fetch_latest_tweets(since_id=since_id)

    if not tweets:
        logger.info("No new @yellow tweets")
        return

    chat_id = TELEGRAM_CHAT_ID
    for tweet in tweets:
        # Filter Yellow Pro
        if is_yellow_pro_content(tweet["text"]):
            logger.info(f"Filtered Yellow Pro tweet: {tweet['id']}")
            save_last_main_tweet_id(tweet["id"])
            continue

        # Post to chat group with discussion prompt
        discussion = await generate_tweet_discussion(tweet["text"])
        if discussion:
            msg = (
                f"<b>@yellow 새 소식</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{escape_html(tweet['text'][:400])}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🔗 {tweet['url']}\n\n"
                f"{discussion}"
            )
        else:
            msg = format_yellow_main_tweet(tweet)

        try:
            await context.bot.send_message(
                chat_id=chat_id, text=msg,
                parse_mode=ParseMode.HTML, disable_web_page_preview=False,
            )
        except Exception as e:
            logger.warning(f"Failed to post @yellow tweet to chat: {e}")

        # Also broadcast to subscribers
        subscribers = subscriber_manager.get_all()
        simple_msg = format_yellow_main_tweet(tweet)
        await _broadcast(context, subscribers, simple_msg)

        save_last_main_tweet_id(tweet["id"])


async def auto_engagement_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Post engagement content to chat group every 30 min (8AM-11PM KST)."""
    if not is_within_posting_hours():
        logger.info("Outside posting hours (8AM-11PM KST), skipping auto-post")
        return

    chat_id = TELEGRAM_CHAT_ID
    post = get_engagement_post()

    logger.info(f"Sending auto engagement post to {chat_id}")
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=post,
            parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        )
    except Exception as e:
        logger.warning(f"Failed to send engagement post: {e}")


async def _broadcast(context: ContextTypes.DEFAULT_TYPE, subscribers: set[int], text: str) -> None:
    for chat_id in subscribers:
        try:
            await context.bot.send_message(
                chat_id=chat_id, text=text,
                disable_web_page_preview=False, parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            logger.warning(f"Failed to send to {chat_id}: {e}")
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
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    if job_queue:
        # @Yellow__Korea tweet checker
        job_queue.run_repeating(
            check_korea_tweets,
            interval=TWITTER_SCRAPE_INTERVAL_MINUTES * 60,
            first=15,
            name="korea_tweet_checker",
        )
        logger.info(f"@Yellow__Korea checker: every {TWITTER_SCRAPE_INTERVAL_MINUTES} min")

        # @yellow main tweet checker
        job_queue.run_repeating(
            check_yellow_main_tweets,
            interval=TWITTER_SCRAPE_INTERVAL_MINUTES * 60,
            first=30,
            name="yellow_main_tweet_checker",
        )
        logger.info(f"@yellow checker: every {TWITTER_SCRAPE_INTERVAL_MINUTES} min")

        # Auto engagement post (30 min, 8AM-11PM KST)
        job_queue.run_repeating(
            auto_engagement_post,
            interval=AUTO_POST_INTERVAL_MINUTES * 60,
            first=60,  # First post after 1 min
            name="auto_engagement",
        )
        logger.info(f"Auto engagement: every {AUTO_POST_INTERVAL_MINUTES} min (8AM-11PM KST)")

    return app
