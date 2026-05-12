"""
Spam/scam filter for incoming chat messages.

크립토 텔레그램 채팅방에 자주 돌아다니는 에어드롭/지갑연결 사기,
"$X,XXX 받으셨다" 식의 가짜 보상 미끼, 의심스러운 포워드 메시지 등을
탐지해서 봇이 호응(축하/리액션)하지 않도록 막는다.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from telegram import Message

logger = logging.getLogger(__name__)


# 사기 미끼 키워드 (한국어 + 영어). 단독으로는 약한 신호.
SCAM_KEYWORDS = (
    # Korean airdrop scam
    "에어드롭", "에어드랍", "에드랍",
    "받으셨", "수령하셨", "당첨되", "선정되셨",
    "지갑 연결", "지갑연결", "월렛 연결", "월렛연결",
    "인증만 하면", "활동만 하면", "클레임", "claim",
    "토큰 분배", "분배 받",
    "리워드 받", "보상 받",
    # English airdrop scam
    "airdrop", "claim now", "claim your", "you received",
    "you won", "you are eligible", "eligible for",
    "free tokens", "connect wallet", "connect your wallet",
    "verify wallet", "verify your wallet",
    # Pump/shill
    "1000x", "100x gem", "pump tomorrow", "pre-sale", "presale",
    "프리세일", "프라이빗 세일", "사전 판매",
)

# 단어 단독으로 거의 100% 스캠인 강한 신호.
STRONG_SCAM_KEYWORDS = (
    "에어드롭 대박", "에어드롭 신청", "에어드롭 수령",
    "지갑만 연결", "지갑 연결만",
    "claim airdrop", "claim your airdrop",
    "airdrop received", "airdrop reward",
)

# "$1,168", "$2,500", "1500 USDT" 같은 보상 금액 패턴.
MONEY_PATTERN = re.compile(
    r"\$\s*\d{1,3}(?:,\d{3})+"          # $1,168 / $12,345
    r"|\$\s*\d{3,}(?:\.\d+)?"           # $500 / $1500.50
    r"|\d{2,}\s*(?:USDT|USDC|BUSD|DAI|ETH|BTC|SOL|ARB|OP|SUI|TIA|STRK)\b",
    re.IGNORECASE,
)

# 자주 사칭되는 에어드롭 프로젝트들.
IMPERSONATED_PROJECTS = (
    "arb airdrop", "arbitrum airdrop",
    "op airdrop", "optimism airdrop",
    "starknet airdrop", "strk airdrop",
    "zksync airdrop", "zk airdrop",
    "layerzero airdrop", "layer zero airdrop", "zro airdrop",
    "sui airdrop", "celestia airdrop", "tia airdrop",
    "blast airdrop", "linea airdrop", "scroll airdrop",
    "ARB 에어드롭", "OP 에어드롭", "Arbitrum 에어드롭",
)

# 포워드 출처가 봇/사기 채널처럼 보이는 이름 조각.
SUSPICIOUS_FORWARD_NAMES = (
    "봇이", "봇 ", " 봇", "에어드롭", "에어드랍",
    "claim", "airdrop", "reward",
    "drop_", "_drop", "drops_", "_drops",
)

# 출처가 신뢰할 만한 옐로우 공식 채널/봇.
TRUSTED_FORWARD_NAMES = (
    "yellow",          # @yellow, Yellow Network
    "yellowkorea",
    "yellow korea",
    "yellow__korea",
    "yellow network",
    "yellow_announcements",
)


def _normalize(text: str) -> str:
    return (text or "").lower()


def _is_trusted_source(name: str) -> bool:
    name = _normalize(name)
    if not name:
        return False
    return any(t in name for t in TRUSTED_FORWARD_NAMES)


def scam_score(text: str) -> int:
    """Return a heuristic scam score. >=3 = treat as scam."""
    if not text:
        return 0

    lower = _normalize(text)
    score = 0

    if MONEY_PATTERN.search(text):
        score += 2

    score += sum(1 for kw in SCAM_KEYWORDS if kw in lower)
    score += 3 * sum(1 for kw in STRONG_SCAM_KEYWORDS if kw in lower)
    score += 2 * sum(1 for kw in IMPERSONATED_PROJECTS if kw.lower() in lower)

    return score


def is_scam_text(text: str) -> bool:
    """True if the text reads like an airdrop/wallet-connect scam."""
    return scam_score(text) >= 3


def get_forward_sender_name(message: "Message") -> Optional[str]:
    """Best-effort extraction of the original forward sender name."""
    if message is None:
        return None

    origin = getattr(message, "forward_origin", None)
    if origin is not None:
        for attr in ("sender_user_name", "author_signature"):
            val = getattr(origin, attr, None)
            if val:
                return val
        sender_user = getattr(origin, "sender_user", None)
        if sender_user is not None:
            name = " ".join(
                p for p in (
                    getattr(sender_user, "first_name", ""),
                    getattr(sender_user, "last_name", ""),
                    getattr(sender_user, "username", ""),
                ) if p
            ).strip()
            if name:
                return name
        sender_chat = getattr(origin, "sender_chat", None)
        if sender_chat is not None:
            return getattr(sender_chat, "title", None) or getattr(sender_chat, "username", None)
        chat = getattr(origin, "chat", None)
        if chat is not None:
            return getattr(chat, "title", None) or getattr(chat, "username", None)

    # python-telegram-bot v20+ deprecated fields, kept as fallback.
    forward_from = getattr(message, "forward_from", None)
    if forward_from is not None:
        return getattr(forward_from, "first_name", None) or getattr(forward_from, "username", None)
    forward_from_chat = getattr(message, "forward_from_chat", None)
    if forward_from_chat is not None:
        return getattr(forward_from_chat, "title", None) or getattr(forward_from_chat, "username", None)
    sender_name = getattr(message, "forward_sender_name", None)
    if sender_name:
        return sender_name

    return None


def is_forwarded(message: "Message") -> bool:
    """True if the message is a Telegram forward."""
    if message is None:
        return False
    return (
        getattr(message, "forward_origin", None) is not None
        or getattr(message, "forward_from", None) is not None
        or getattr(message, "forward_from_chat", None) is not None
        or bool(getattr(message, "forward_sender_name", None))
    )


def should_ignore(message: "Message") -> bool:
    """Decide whether the bot should stay silent for this message."""
    if message is None or not getattr(message, "text", None):
        return False

    text = message.text

    if is_scam_text(text):
        logger.info("Spam filter: scam content detected, ignoring (preview=%r)", text[:80])
        return True

    if is_forwarded(message):
        sender_name = get_forward_sender_name(message) or ""
        if _is_trusted_source(sender_name):
            return False

        lower_name = _normalize(sender_name)
        looks_like_bot_source = any(p in lower_name for p in SUSPICIOUS_FORWARD_NAMES) if lower_name else False

        # 출처 이름이 봇/에어드롭 같으면 무조건 무시.
        if looks_like_bot_source:
            logger.info(
                "Spam filter: forwarded from suspicious source %r, ignoring",
                sender_name,
            )
            return True

        # 출처 이름은 평범해도 본문에 약한 스캠 신호가 있으면 무시 (낮은 임계값).
        if scam_score(text) >= 2:
            logger.info(
                "Spam filter: forwarded message with scam signals, ignoring (from=%r)",
                sender_name or "unknown",
            )
            return True

    return False
