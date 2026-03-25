"""
Yellow Korea Telegram Bot.
Scrapes @YellowKorea_ann channel and delivers info to users with auto-engagement.
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

from src.config import (
    TELEGRAM_BOT_TOKEN,
    SCRAPE_INTERVAL_MINUTES,
    AUTO_TIP_INTERVAL_MINUTES,
)
from src.yellow_knowledge import YellowChatHandler, YELLOW_INFO, get_random_tip
from src.subscribers import SubscriberManager
from src.telegram_scraper import (
    TelegramChannelScraper,
    get_last_msg_id,
    save_last_msg_id,
)

logger = logging.getLogger(__name__)

# Global instances
chat_handler = YellowChatHandler()
subscriber_manager = SubscriberManager()
channel_scraper = TelegramChannelScraper()


# ──────────────────────────────────────────────
# Command Handlers
# ──────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    user_name = user.first_name if user else "유저"

    welcome_text = (
        f"안녕하세요 {user_name}님!\n"
        f"Yellow Korea Bot에 오신 것을 환영합니다!\n\n"
        f"이 봇은 Yellow Korea 공지방의 최신 소식을 실시간으로 전달하고,\n"
        f"Yellow Network에 대한 정보를 제공합니다.\n\n"
        f"주요 기능:\n"
        f"- Yellow Korea 공지방 실시간 알림\n"
        f"- Yellow Network 정보 제공\n"
        f"- Yellow 관련 질문 답변\n"
        f"- 정기적인 Yellow 소식 & 팁\n\n"
        f"바로 /subscribe 를 눌러 알림을 구독하세요!"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "Yellow Korea 공지방", url="https://t.me/YellowKorea_ann"
            ),
            InlineKeyboardButton("Twitter/X", url="https://x.com/Yellow__Korea"),
        ],
        [
            InlineKeyboardButton("알림 구독하기", callback_data="subscribe"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    # Auto-subscribe on first start
    chat_id = update.effective_chat.id
    if subscriber_manager.add(chat_id):
        await update.message.reply_text(
            "자동으로 알림이 구독되었습니다!\n"
            "공지방의 새 소식이 올라오면 바로 알려드릴게요.\n"
            "해제하려면 /unsubscribe 를 입력하세요."
        )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "사용 가능한 명령어:\n\n"
        "/start - 봇 시작 & 소개\n"
        "/about - Yellow Network 소개\n"
        "/links - 공식 링크 모음\n"
        "/subscribe - 공지 알림 구독\n"
        "/unsubscribe - 공지 알림 해제\n"
        "/latest - 최근 공지 보기\n"
        "/tip - Yellow 팁 받기\n"
        "/help - 도움말\n\n"
        "또는 자유롭게 Yellow에 대해 질문해주세요!\n"
        "어떤 메시지든 보내시면 Yellow 관련 정보로 답변드립니다."
    )
    await update.message.reply_text(help_text)


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    text = (
        f"Yellow Network 소개\n\n"
        f"{YELLOW_INFO['about']}\n\n"
        f"주요 기능:\n{YELLOW_INFO['features']}\n\n"
        f"토큰:\n{YELLOW_INFO['token']}\n\n"
        f"공지방에서 최신 업데이트를 확인하세요!\n"
        f"https://t.me/YellowKorea_ann"
    )
    await update.message.reply_text(text)


async def cmd_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /links command."""
    keyboard = [
        [
            InlineKeyboardButton(
                "Yellow Korea 공지방", url="https://t.me/YellowKorea_ann"
            ),
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
            "공지 알림을 구독했습니다!\n"
            "Yellow Korea 공지방의 새 소식이 올라오면 바로 알려드릴게요."
        )
    else:
        await update.message.reply_text("이미 공지 알림을 구독 중입니다!")


async def cmd_unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unsubscribe command."""
    chat_id = update.effective_chat.id
    if subscriber_manager.remove(chat_id):
        await update.message.reply_text(
            "공지 알림 구독을 해제했습니다.\n"
            "다시 구독하려면 /subscribe 를 입력하세요."
        )
    else:
        await update.message.reply_text("현재 공지 알림을 구독하고 있지 않습니다.")


async def cmd_latest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /latest command - show recent channel posts."""
    await update.message.reply_text("최근 공지를 가져오는 중...")

    try:
        posts = await channel_scraper.fetch_recent_posts(count=5)
        if not posts:
            await update.message.reply_text(
                "최근 공지를 가져올 수 없습니다.\n"
                "직접 확인해주세요: https://t.me/YellowKorea_ann"
            )
            return

        for post in posts:
            text = format_channel_message(post)
            await update.message.reply_text(text, disable_web_page_preview=False)

    except Exception as e:
        logger.error(f"Error fetching latest posts: {e}")
        await update.message.reply_text(
            "공지를 가져오는 중 오류가 발생했습니다.\n"
            "직접 확인해주세요: https://t.me/YellowKorea_ann"
        )


async def cmd_tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tip command - send a random Yellow tip."""
    tip = get_random_tip()
    await update.message.reply_text(tip)


# ──────────────────────────────────────────────
# Callback Query Handler
# ──────────────────────────────────────────────


async def callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == "subscribe":
        chat_id = update.effective_chat.id
        if subscriber_manager.add(chat_id):
            await query.edit_message_text(
                query.message.text + "\n\n공지 알림을 구독했습니다!"
            )
        else:
            await query.answer("이미 구독 중입니다!", show_alert=True)


# ──────────────────────────────────────────────
# Message Handler (Chat with users)
# ──────────────────────────────────────────────


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle regular text messages - chat about Yellow."""
    if not update.message or not update.message.text:
        return

    user_message = update.message.text
    user = update.effective_user
    user_name = user.first_name if user else ""

    response = await chat_handler.get_response(user_message, user_name=user_name)
    await update.message.reply_text(response)


# ──────────────────────────────────────────────
# Channel Message Broadcasting
# ──────────────────────────────────────────────


def format_channel_message(post: dict) -> str:
    """Format a channel post into a Telegram message for subscribers."""
    preview = post["text"]
    if len(preview) > 500:
        preview = preview[:500] + "..."

    text = (
        f"Yellow Korea 공지\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{preview}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"원문 보기: {post['channel_url']}"
    )
    return text


async def check_and_broadcast_channel(
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Scheduled job: check for new channel posts and broadcast to subscribers."""
    logger.info("Checking for new channel posts...")

    since_id = get_last_msg_id()
    messages = await channel_scraper.fetch_latest_messages(since_id=since_id)

    if not messages:
        logger.info("No new channel posts found")
        return

    subscribers = subscriber_manager.get_all()
    logger.info(
        f"Found {len(messages)} new posts, broadcasting to {len(subscribers)} subscribers"
    )

    for msg in messages:
        text = format_channel_message(msg)

        for chat_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    disable_web_page_preview=False,
                )
            except Exception as e:
                logger.warning(f"Failed to send to {chat_id}: {e}")
                if "Forbidden" in str(e) or "blocked" in str(e).lower():
                    subscriber_manager.remove(chat_id)

        save_last_msg_id(msg["id"])

    logger.info("Channel broadcast complete")


# ──────────────────────────────────────────────
# Auto-Engagement: Periodic Yellow Tips
# ──────────────────────────────────────────────


async def send_periodic_tip(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: send a random Yellow tip to all subscribers."""
    subscribers = subscriber_manager.get_all()
    if not subscribers:
        return

    tip = get_random_tip()
    logger.info(f"Sending periodic tip to {len(subscribers)} subscribers")

    for chat_id in subscribers:
        try:
            await context.bot.send_message(chat_id=chat_id, text=tip)
        except Exception as e:
            logger.warning(f"Failed to send tip to {chat_id}: {e}")
            if "Forbidden" in str(e) or "blocked" in str(e).lower():
                subscriber_manager.remove(chat_id)


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
    app.add_handler(CommandHandler("tip", cmd_tip))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Message handler (must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Schedule jobs
    job_queue = app.job_queue
    if job_queue:
        # Check channel for new posts
        job_queue.run_repeating(
            check_and_broadcast_channel,
            interval=SCRAPE_INTERVAL_MINUTES * 60,
            first=10,
            name="channel_checker",
        )
        logger.info(f"Channel checker scheduled every {SCRAPE_INTERVAL_MINUTES} min")

        # Periodic Yellow tips
        job_queue.run_repeating(
            send_periodic_tip,
            interval=AUTO_TIP_INTERVAL_MINUTES * 60,
            first=AUTO_TIP_INTERVAL_MINUTES * 60,  # First tip after full interval
            name="auto_tip",
        )
        logger.info(f"Auto-tip scheduled every {AUTO_TIP_INTERVAL_MINUTES} min")
    else:
        logger.warning("Job queue not available. Scheduled tasks disabled.")

    return app
