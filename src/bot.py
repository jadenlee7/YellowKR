"""
Yellow Korea Telegram Bot.
Scrapes @Yellow__Korea + @yellow Twitter, AI chat, auto-engagement posts.
"""

import logging
import re
import time
from datetime import datetime, time as dtime, timezone, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions,
)
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
    OWNER_TELEGRAM_ID,
    TWITTER_SCRAPE_INTERVAL_MINUTES,
    AUTO_POST_INTERVAL_MINUTES,
    MIN_HUMAN_MSGS_BEFORE_POST,
    MAX_AUTO_POSTS_PER_DAY,
    SPAM_ACTION,
    SPAM_MUTE_THRESHOLD,
    SPAM_MUTE_MINUTES,
    DAILY_REPORT_HOUR_KST,
    WEEKLY_REPORT_ENABLED,
    CAPTCHA_ENABLED,
    CAPTCHA_TIMEOUT_SECONDS,
    CAPTCHA_FAIL_ACTION,
    TWITTER_MAIN_USERNAME,
)
from src.yellow_knowledge import (
    YellowChatHandler,
    YELLOW_INFO,
    is_yellow_related,
    generate_daily_insight,
)
from src.faq import match_faq
from src.subscribers import SubscriberManager
from src.stats import StatsManager, KST
from src.moderation import (
    check_message as spam_check,
    is_suspicious_name,
    FloodTracker,
    WarningTracker,
)
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

logger = logging.getLogger(__name__)

chat_handler = YellowChatHandler()
subscriber_manager = SubscriberManager()
stats_manager = StatsManager()
flood_tracker = FloodTracker()
warning_tracker = WarningTracker()
twitter_scraper = TwitterScraper()
# Separate scraper for @yellow main account
yellow_main_scraper = TwitterScraper(username_override=TWITTER_MAIN_USERNAME)

# Cached numeric chat id for the main group (resolved from TELEGRAM_CHAT_ID).
_main_chat_id: int | None = None
# Cached per-chat admin id sets: chat_id -> (fetched_at_monotonic, {user_ids}).
_admin_cache: dict[int, tuple[float, set[int]]] = {}
ADMIN_CACHE_TTL = 600  # seconds


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
# Helpers: ownership, admin status, temp messages
# ──────────────────────────────────────────────


def _is_owner(user_id: int) -> bool:
    return bool(OWNER_TELEGRAM_ID) and str(user_id) == str(OWNER_TELEGRAM_ID)


async def _resolve_main_chat_id(context: ContextTypes.DEFAULT_TYPE):
    """Resolve TELEGRAM_CHAT_ID (which may be an @username) to a numeric id once."""
    global _main_chat_id
    if _main_chat_id is not None:
        return _main_chat_id
    try:
        chat = await context.bot.get_chat(TELEGRAM_CHAT_ID)
        _main_chat_id = chat.id
    except Exception as e:
        logger.warning(f"Could not resolve main chat id from {TELEGRAM_CHAT_ID}: {e}")
    return _main_chat_id


async def _is_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    """Whether user is an admin/creator of the chat (cached, with TTL)."""
    now = time.monotonic()
    cached = _admin_cache.get(chat_id)
    if cached and now - cached[0] <= ADMIN_CACHE_TTL:
        return user_id in cached[1]
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        ids = {a.user.id for a in admins}
        _admin_cache[chat_id] = (now, ids)
        return user_id in ids
    except Exception as e:
        logger.warning(f"Could not fetch admins for {chat_id}: {e}")
        return user_id in cached[1] if cached else False


async def _delete_msg_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    d = context.job.data
    try:
        await context.bot.delete_message(d["chat_id"], d["message_id"])
    except Exception:
        pass


async def _send_temp(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str,
                     delete_after: int = 30) -> None:
    """Send a short notice and auto-delete it to keep the room clean."""
    try:
        sent = await context.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
    except Exception:
        return
    if context.job_queue:
        context.job_queue.run_once(
            _delete_msg_job, delete_after,
            data={"chat_id": chat_id, "message_id": sent.message_id},
        )


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
        "/top - 활동 리더보드 (오늘)\n"
        "/help - 도움말\n\n"
        "Yellow 관련 질문에 AI가 답변해드립니다!"
    )
    # Owner-only commands shown privately to the owner.
    user = update.effective_user
    if user and _is_owner(user.id):
        help_text += (
            "\n\n<b>운영자 전용:</b>\n"
            "/report - 오늘 활동 요약 DM 받기\n"
            "/stats - 오늘 통계 보기\n"
            "/myid - 내 텔레그램 ID 확인"
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
# Stats / Leaderboard / Owner Commands
# ──────────────────────────────────────────────


def _format_leaderboard(rows: list[tuple[str, int]]) -> str:
    if not rows:
        return "아직 집계된 활동이 없어요."
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, (label, count) in enumerate(rows):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{prefix} {escape_html(label)} — {count}")
    return "\n".join(lines)


def build_report_text(summary: dict, insight: str | None = None) -> str:
    lines = [
        "<b>📊 Yellow Korea 데일리 리포트</b>",
        f"📅 {summary['date']}",
        "",
        f"💬 총 메시지: <b>{summary['messages']}</b>",
        f"👥 활성 유저: <b>{summary['active_users']}</b>명",
        f"🆕 신규 입장: <b>{summary['new_members']}</b>명",
        f"🛡️ 스팸 차단: <b>{summary['spam_removed']}</b>건",
        f"⚡ FAQ 자동응답: <b>{summary.get('faq_hits', 0)}</b>건",
        "",
    ]
    if summary["leaderboard"]:
        lines.append("<b>🏆 활동 리더보드</b>")
        lines.append(_format_leaderboard(summary["leaderboard"]))
        lines.append("")
    if summary["keywords"]:
        kw = ", ".join(f"{escape_html(w)}({c})" for w, c in summary["keywords"])
        lines.append("<b>🔥 화제 키워드</b>")
        lines.append(kw)
        lines.append("")
    if summary["questions"]:
        lines.append("<b>❓ 유저 질문</b>")
        for q in summary["questions"][:5]:
            lines.append(f"• {escape_html(q[:120])}")
        lines.append("")
    if insight:
        lines.append("<b>🤖 인사이트 &amp; 추천 메시지</b>")
        lines.append(escape_html(insight))
    return "\n".join(lines)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = stats_manager.get_leaderboard(n=10)
    text = (
        "<b>🏆 오늘의 활동 리더보드</b>\n\n"
        f"{_format_leaderboard(rows)}\n\n"
        "<i>가장 활발하게 대화에 참여한 멤버들이에요!</i>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    uid = user.id if user else "?"
    text = (
        f"당신의 텔레그램 ID: <code>{uid}</code>\n\n"
        f"데일리 리포트를 받으려면 이 값을 "
        f"<code>OWNER_TELEGRAM_ID</code> 환경 변수로 설정하세요."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not _is_owner(user.id):
        return  # owner-only, silently ignored for others
    summary = stats_manager.day_summary()
    await update.message.reply_text(build_report_text(summary), parse_mode=ParseMode.HTML)


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not _is_owner(user.id):
        return  # owner-only
    await update.message.reply_text("오늘 활동 요약을 생성 중...")
    summary = stats_manager.day_summary()
    insight = await _build_insight(summary)
    await update.message.reply_text(
        build_report_text(summary, insight), parse_mode=ParseMode.HTML
    )


async def _build_insight(summary: dict) -> str | None:
    """Ask Claude for a one-line read + a suggested next info message."""
    if not summary["keywords"] and not summary["questions"]:
        return None
    kw = ", ".join(w for w, _ in summary["keywords"])
    questions = "\n".join(f"- {q}" for q in summary["questions"][:10])
    summary_text = (
        f"오늘 자주 나온 키워드: {kw or '없음'}\n"
        f"유저들이 한 질문:\n{questions or '없음'}\n"
        f"총 메시지 {summary['messages']}개, 활성 유저 {summary['active_users']}명."
    )
    return await generate_daily_insight(summary_text)


async def send_daily_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job: DM the owner yesterday's activity summary."""
    if not OWNER_TELEGRAM_ID:
        logger.warning("OWNER_TELEGRAM_ID not set; skipping daily report DM.")
        return
    yesterday = (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
    summary = stats_manager.day_summary(yesterday)
    insight = await _build_insight(summary)
    text = build_report_text(summary, insight)
    try:
        await context.bot.send_message(
            chat_id=int(OWNER_TELEGRAM_ID), text=text, parse_mode=ParseMode.HTML
        )
        logger.info("Sent daily report to owner.")
    except Exception as e:
        logger.warning(f"Failed to send daily report DM: {e}")


# Day-of-week trend bars (Mon→Sun), scaled to the busiest day.
def _trend_block(trend: list[tuple[str, int]]) -> str:
    if not trend:
        return ""
    peak = max((c for _, c in trend), default=0) or 1
    dow = ["월", "화", "수", "목", "금", "토", "일"]
    lines = []
    for date_str, count in trend:
        try:
            wd = datetime.strptime(date_str, "%Y-%m-%d").weekday()
            label = dow[wd]
        except ValueError:
            label = date_str[5:]
        bars = "▇" * round(8 * count / peak) if count else ""
        lines.append(f"{label} {bars} {count}")
    return "\n".join(lines)


def build_weekly_report_text(summary: dict, insight: str | None = None) -> str:
    lines = [
        "<b>📈 Yellow Korea 주간 리포트</b>",
        f"📅 {summary['start']} ~ {summary['end']}",
        "",
        f"💬 주간 메시지: <b>{summary['messages']}</b>",
        f"👥 활성 유저: <b>{summary['active_users']}</b>명",
        f"🆕 신규 입장: <b>{summary['new_members']}</b>명",
        f"🛡️ 스팸 차단: <b>{summary['spam_removed']}</b>건",
        f"⚡ FAQ 자동응답: <b>{summary['faq_hits']}</b>건",
        "",
    ]
    trend = _trend_block(summary["trend"])
    if trend:
        lines.append("<b>📊 요일별 활동</b>")
        lines.append(f"<code>{escape_html(trend)}</code>")
        lines.append("")
    if summary["leaderboard"]:
        lines.append("<b>🏆 주간 활동 리더보드</b>")
        lines.append(_format_leaderboard(summary["leaderboard"]))
        lines.append("")
    if summary["keywords"]:
        kw = ", ".join(f"{escape_html(w)}({c})" for w, c in summary["keywords"])
        lines.append("<b>🔥 주간 화제 키워드</b>")
        lines.append(kw)
        lines.append("")
    if insight:
        lines.append("<b>🤖 주간 인사이트 &amp; 추천 방향</b>")
        lines.append(escape_html(insight))
    return "\n".join(lines)


async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled daily; only fires the weekly DM on Mondays (last 7 days)."""
    if not WEEKLY_REPORT_ENABLED or not OWNER_TELEGRAM_ID:
        return
    if datetime.now(KST).weekday() != 0:  # 0 = Monday
        return
    summary = stats_manager.week_summary()
    insight = None
    if summary["keywords"]:
        kw = ", ".join(w for w, _ in summary["keywords"])
        summary_text = (
            f"지난 7일 화제 키워드: {kw}\n"
            f"주간 메시지 {summary['messages']}개, 활성 유저 {summary['active_users']}명, "
            f"신규 입장 {summary['new_members']}명.\n"
            f"이번 주 커뮤니티 트렌드를 한 줄로 요약하고, 다음 주에 집중하면 좋을 "
            f"주제/콘텐츠 방향 1~2개를 제안해줘."
        )
        insight = await generate_daily_insight(summary_text)
    text = build_weekly_report_text(summary, insight)
    try:
        await context.bot.send_message(
            chat_id=int(OWNER_TELEGRAM_ID), text=text, parse_mode=ParseMode.HTML
        )
        logger.info("Sent weekly report to owner.")
    except Exception as e:
        logger.warning(f"Failed to send weekly report DM: {e}")


# ──────────────────────────────────────────────
# Callback / Message Handlers
# ──────────────────────────────────────────────


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data or ""

    # New-member captcha verification (answers the query itself).
    if data.startswith("verify:"):
        await _handle_verify(update, context, data)
        return

    await query.answer()

    if data == "subscribe":
        chat_id = update.effective_chat.id
        if subscriber_manager.add(chat_id):
            await query.edit_message_text(
                query.message.text + "\n\n트윗 알림을 구독했습니다!"
            )
        else:
            await query.answer("이미 구독 중입니다!", show_alert=True)


def _should_reply(msg, text: str, bot_id: int, bot_username: str | None) -> bool:
    """In a group, the bot only chimes in when the message is Yellow-related,
    mentions the bot, or replies to the bot. Avoids replying to everything."""
    reply_to = msg.reply_to_message
    if reply_to and reply_to.from_user and reply_to.from_user.id == bot_id:
        return True
    if bot_username and f"@{bot_username}".lower() in text.lower():
        return True
    return is_yellow_related(text)


async def _handle_spam(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       reason: str) -> None:
    """Delete spam, warn, and mute repeat offenders (per SPAM_ACTION)."""
    msg = update.message
    chat = update.effective_chat
    user = update.effective_user

    stats_manager.record_spam_removed()
    logger.info(f"Spam from {user.id} in {chat.id}: {reason}")

    if SPAM_ACTION != "delete":
        return  # "report" mode: counted in stats only, message left in place

    try:
        await context.bot.delete_message(chat.id, msg.message_id)
    except Exception as e:
        logger.warning(f"Could not delete spam (bot needs admin + delete rights): {e}")

    count = warning_tracker.add(user.id)
    name = escape_html(user.first_name or "유저")

    if count >= SPAM_MUTE_THRESHOLD:
        try:
            until = datetime.now(timezone.utc) + timedelta(minutes=SPAM_MUTE_MINUTES)
            await context.bot.restrict_chat_member(
                chat.id, user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until,
            )
            await _send_temp(
                context, chat.id,
                f"🔇 {name}님 반복적인 스팸/홍보로 {SPAM_MUTE_MINUTES}분간 발언이 제한됩니다.",
                delete_after=60,
            )
            return
        except Exception as e:
            logger.warning(f"Could not mute {user.id} (bot needs restrict rights): {e}")

    await _send_temp(
        context, chat.id,
        f"⚠️ {name}님, 스팸/홍보성 메시지로 판단되어 삭제했어요. 반복 시 발언이 제한됩니다.",
        delete_after=30,
    )


# Full messaging permissions used to lift a captcha mute on success.
_OPEN_PERMS = ChatPermissions(
    can_send_messages=True,
    can_send_polls=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Count joins; run button-click captcha (if enabled) to block mass bot joins."""
    msg = update.message
    if not msg or not msg.new_chat_members:
        return
    chat_id = update.effective_chat.id
    for member in msg.new_chat_members:
        if member.is_bot:
            continue
        stats_manager.record_new_member()
        name = member.first_name or ""
        if is_suspicious_name(name):
            logger.info(f"Suspicious new member name (possible impersonator): {name}")

        if CAPTCHA_ENABLED:
            await _start_captcha(context, chat_id, member)
        else:
            await _send_temp(
                context, chat_id,
                f"👋 {escape_html(name or '유저')}님 환영합니다! 궁금한 건 편하게 물어보세요.",
                delete_after=120,
            )


async def _start_captcha(context: ContextTypes.DEFAULT_TYPE, chat_id: int, member) -> None:
    """Mute the new member and post a verify button; schedule a timeout."""
    name = escape_html(member.first_name or "유저")

    # Mute until verified. If the bot can't restrict, fall back to a welcome.
    try:
        await context.bot.restrict_chat_member(
            chat_id, member.id, permissions=ChatPermissions(can_send_messages=False)
        )
    except Exception as e:
        logger.warning(f"Captcha: cannot restrict new member (bot needs admin?): {e}")
        await _send_temp(
            context, chat_id,
            f"👋 {name}님 환영합니다! 궁금한 건 편하게 물어보세요.",
            delete_after=120,
        )
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("저는 사람입니다 ✅", callback_data=f"verify:{member.id}")]]
    )
    text = (
        f"👋 {name}님 환영합니다!\n"
        f"스팸 봇 방지를 위해 <b>{CAPTCHA_TIMEOUT_SECONDS}초</b> 안에 아래 버튼을 눌러 인증해주세요."
    )
    try:
        sent = await context.bot.send_message(
            chat_id, text, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Captcha: could not send prompt: {e}")
        return

    if context.job_queue:
        context.job_queue.run_once(
            _captcha_timeout, CAPTCHA_TIMEOUT_SECONDS,
            data={"chat_id": chat_id, "user_id": member.id, "message_id": sent.message_id},
            name=f"captcha:{chat_id}:{member.id}",
        )


async def _handle_verify(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    """Handle a captcha verify-button tap. Only the joining user may verify."""
    query = update.callback_query
    chat_id = update.effective_chat.id
    try:
        target_id = int(data.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer()
        return

    clicker = update.effective_user
    if clicker is None or clicker.id != target_id:
        await query.answer("본인만 인증할 수 있어요.", show_alert=True)
        return

    try:
        await context.bot.restrict_chat_member(chat_id, target_id, permissions=_OPEN_PERMS)
    except Exception as e:
        logger.warning(f"Captcha: could not lift restriction: {e}")

    await query.answer("인증 완료! 환영합니다 🎉")

    # Cancel the pending timeout job and delete the prompt.
    if context.job_queue:
        for job in context.job_queue.get_jobs_by_name(f"captcha:{chat_id}:{target_id}"):
            job.schedule_removal()
    try:
        await query.message.delete()
    except Exception:
        pass

    await _send_temp(
        context, chat_id,
        f"✅ {escape_html(clicker.first_name or '유저')}님 인증 완료! "
        f"Yellow Korea에 오신 걸 환영합니다 🎉 궁금한 건 편하게 물어보세요.",
        delete_after=120,
    )


async def _captcha_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """New member didn't verify in time: delete the prompt and kick/keep muted."""
    d = context.job.data
    chat_id, user_id, message_id = d["chat_id"], d["user_id"], d["message_id"]

    try:
        await context.bot.delete_message(chat_id, message_id)
    except Exception:
        pass

    if CAPTCHA_FAIL_ACTION == "kick":
        try:
            # Ban then immediately unban so they're removed but can rejoin later.
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
            logger.info(f"Captcha: kicked unverified member {user_id}")
        except Exception as e:
            logger.warning(f"Captcha: could not kick {user_id} (bot needs ban rights): {e}")
    else:
        logger.info(f"Captcha: member {user_id} left muted (no verification)")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    chat = update.effective_chat
    user = update.effective_user

    # Private chat: only reply to Yellow-related messages (commands handled
    # separately). Replying to everything just clutters the conversation.
    if chat.type == "private":
        if not is_yellow_related(msg.text):
            return
        # Auto-FAQ: answer common questions from a canned response (no API call).
        faq = match_faq(msg.text)
        if faq:
            stats_manager.record_faq_hit()
            await msg.reply_text(faq, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            return
        response = md_to_html(await chat_handler.get_response(
            msg.text, user_name=user.first_name if user else ""
        ))
        try:
            await msg.reply_text(response, parse_mode=ParseMode.HTML)
        except Exception:
            await msg.reply_text(response)
        return

    # Group/supergroup. Ignore anonymous admins / channel posts / other bots.
    if user is None or user.is_bot:
        return

    text = msg.text
    is_admin = await _is_admin(context, chat.id, user.id)

    # 1. Anti-spam (admins exempt).
    if SPAM_ACTION != "off" and not is_admin and not _is_owner(user.id):
        flood_reason = flood_tracker.check(user.id, text)
        if flood_reason:
            await _handle_spam(update, context, flood_reason)
            return
        user_total = stats_manager.data.get("users", {}).get(str(user.id), {}).get("total", 0)
        verdict = spam_check(text, display_name=user.first_name or "", user_msg_count=user_total)
        if verdict.is_spam:
            await _handle_spam(update, context, "; ".join(verdict.reasons))
            return

    # 2. Record activity for leaderboard / stats / post gating.
    stats_manager.record_message(chat.id, user, text)

    # 3. Reply only to Yellow-related messages (or mentions / replies to bot).
    if not _should_reply(msg, text, context.bot.id, context.bot.username):
        return

    # 4. Auto-FAQ: short, common questions get a canned answer (saves API cost).
    faq = match_faq(text)
    if faq:
        stats_manager.record_faq_hit()
        try:
            await msg.reply_text(faq, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except Exception:
            await msg.reply_text(faq)
        return

    response = md_to_html(await chat_handler.get_response(text, user_name=user.first_name or ""))
    try:
        await msg.reply_text(response, parse_mode=ParseMode.HTML)
    except Exception:
        await msg.reply_text(response)


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

    chat_id = await _resolve_main_chat_id(context) or TELEGRAM_CHAT_ID
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
            # Event-driven bot post: reset the gating counter so an auto-post
            # won't immediately stack on top of this one.
            if isinstance(chat_id, int):
                stats_manager.note_bot_message(chat_id)
        except Exception as e:
            logger.warning(f"Failed to post @yellow tweet to chat: {e}")

        # Also broadcast to subscribers
        subscribers = subscriber_manager.get_all()
        simple_msg = format_yellow_main_tweet(tweet)
        await _broadcast(context, subscribers, simple_msg)

        save_last_main_tweet_id(tweet["id"])


async def auto_engagement_post(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Occasionally post engagement content, but only when the room has been
    active and the bot wasn't the last to speak (no talking to itself)."""
    if not is_within_posting_hours():
        logger.info("Outside posting hours (8AM-11PM KST), skipping auto-post")
        return

    chat_id = await _resolve_main_chat_id(context)
    if chat_id is None:
        logger.warning("Main chat id unresolved; skipping auto-post")
        return

    if not stats_manager.should_auto_post(
        chat_id, MIN_HUMAN_MSGS_BEFORE_POST, MAX_AUTO_POSTS_PER_DAY
    ):
        logger.info("Auto-post gated: chat quiet or daily cap reached.")
        return

    post = get_engagement_post()
    logger.info(f"Sending auto engagement post to {chat_id}")
    try:
        await context.bot.send_message(
            chat_id=chat_id, text=post,
            parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        )
        stats_manager.record_auto_post(chat_id)
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
    app.add_handler(CommandHandler("top", cmd_top))
    app.add_handler(CommandHandler("myid", cmd_myid))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members)
    )
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

        # Auto engagement post (gated: only when chat is active, capped per day)
        job_queue.run_repeating(
            auto_engagement_post,
            interval=AUTO_POST_INTERVAL_MINUTES * 60,
            first=300,  # First check after 5 min
            name="auto_engagement",
        )
        logger.info(
            f"Auto engagement: check every {AUTO_POST_INTERVAL_MINUTES} min, "
            f"max {MAX_AUTO_POSTS_PER_DAY}/day, needs {MIN_HUMAN_MSGS_BEFORE_POST} human msgs"
        )

        # Daily owner report DM (default 9AM KST)
        job_queue.run_daily(
            send_daily_report,
            time=dtime(hour=DAILY_REPORT_HOUR_KST, minute=0, tzinfo=KST),
            name="daily_report",
        )
        logger.info(f"Daily report: {DAILY_REPORT_HOUR_KST}:00 KST -> owner DM")

        # Weekly owner report DM (checked daily, fires only on Mondays)
        if WEEKLY_REPORT_ENABLED:
            job_queue.run_daily(
                send_weekly_report,
                time=dtime(hour=DAILY_REPORT_HOUR_KST, minute=5, tzinfo=KST),
                name="weekly_report",
            )
            logger.info(f"Weekly report: Mondays {DAILY_REPORT_HOUR_KST}:05 KST -> owner DM")

    return app
