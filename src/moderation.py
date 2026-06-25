"""
Anti-spam moderation for the Yellow Korea chat group.

Uses a lightweight scoring heuristic (no API calls) to catch the spam that
actually hits crypto Telegram groups: phishing/airdrop scams, "DM the admin"
impersonation, mass-tagging, invite-link spam, and link-dropping by brand-new
accounts. Group admins are always exempt. Official Yellow links are whitelisted.
"""

import logging
import re
import time

logger = logging.getLogger(__name__)

# Score at/above this threshold => treated as spam.
SPAM_THRESHOLD = 5

# Links that are always allowed (official Yellow channels).
LINK_WHITELIST = (
    "t.me/yellowkorea_ann",
    "t.me/yellowkorea_chat",
    "x.com/yellow",
    "x.com/yellow__korea",
    "twitter.com/yellow",
    "yellow.org",
)

# High-signal scam phrases (Korean + English). Each match adds points.
SCAM_PHRASES = (
    # airdrop / giveaway bait
    "에어드랍", "에어드롭", "airdrop", "무료 지급", "무료지급", "공짜", "당첨",
    "이벤트 당첨", "선착순", "free claim", "claim now", "claim your", "giveaway",
    # impersonation / off-platform contact
    "관리자에게 dm", "운영자에게 dm", "관리자 dm", "1:1 문의", "고객센터",
    "고객지원", "support team", "contact admin", "dm me", "텔레 @", "텔레그램 @",
    "개인 연락", "개인톡", "오픈톡", "오픈채팅",
    # wallet phishing
    "지갑 연결", "지갑연결", "지갑 인증", "지갑 동기화", "동기화", "복구", "검증",
    "seed phrase", "private key", "비밀키", "시드", "복구 문구", "connect wallet",
    "validate wallet", "sync wallet", "메타마스크 인증", "kyc 인증",
    # high-yield / pump scams
    "고수익", "수익 보장", "수익보장", "원금 보장", "리딩방", "리딩 방", "코인 추천",
    "추천방", "선물 거래", "고배율", "단타방", "100% 수익", "보장", "guaranteed",
    "double your", "x2", "x10", "투자 문의", "수익률",
)

# Username/display-name patterns used by impersonators.
IMPERSONATION_NAMES = (
    "admin", "관리자", "운영자", "운영팀", "support", "고객센터", "moderator",
    "yellow support", "yellow admin", "official",
)

_URL_RE = re.compile(r"(https?://\S+|t\.me/\S+|www\.\S+|\b\S+\.(?:com|org|net|io|xyz|me|app|finance|click|top|vip)\b)", re.I)
_MENTION_RE = re.compile(r"@\w+")
# Mixed/cyrillic-homoglyph or excessive emoji often signal spam bots.
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


class SpamVerdict:
    def __init__(self, is_spam: bool, score: int, reasons: list[str]):
        self.is_spam = is_spam
        self.score = score
        self.reasons = reasons


def is_suspicious_name(display_name: str) -> bool:
    """True if a display name impersonates staff/official (admin, support, etc.)."""
    if not display_name:
        return False
    low = display_name.lower()
    return any(n in low for n in IMPERSONATION_NAMES)


def _has_nonwhitelisted_link(text: str) -> bool:
    low = text.lower()
    for m in _URL_RE.finditer(low):
        url = m.group(0)
        if not any(w in url for w in LINK_WHITELIST):
            return True
    return False


def check_message(text: str, display_name: str = "", user_msg_count: int = 0) -> SpamVerdict:
    """Score a message. `user_msg_count` is the author's lifetime message count
    (new accounts are held to a stricter standard)."""
    if not text:
        return SpamVerdict(False, 0, [])

    low = text.lower()
    score = 0
    reasons: list[str] = []
    is_new_user = user_msg_count < 3

    # Scam phrases.
    hits = [p for p in SCAM_PHRASES if p in low]
    if hits:
        score += 3 + (len(hits) - 1)
        reasons.append(f"scam phrase: {hits[0]}")

    # Links.
    if _has_nonwhitelisted_link(low):
        score += 2
        reasons.append("external link")
        if is_new_user:
            score += 3
            reasons.append("link from new user")

    # Mass mentions (tagging many users).
    mentions = _MENTION_RE.findall(text)
    if len(mentions) >= 5:
        score += 3
        reasons.append(f"mass mention x{len(mentions)}")

    # Impersonation by display name.
    name_low = display_name.lower()
    if any(n in name_low for n in IMPERSONATION_NAMES):
        score += 2
        reasons.append("suspicious display name")
        if _has_nonwhitelisted_link(low) or hits:
            score += 3
            reasons.append("impersonator pushing link/scam")

    # Cyrillic homoglyphs in an otherwise Korean/English room.
    if _CYRILLIC_RE.search(text):
        score += 2
        reasons.append("cyrillic homoglyphs")

    return SpamVerdict(score >= SPAM_THRESHOLD, score, reasons)


class FloodTracker:
    """Detects message flooding: too many messages in a short window, or the
    same message repeated."""

    def __init__(self, max_msgs: int = 6, window_sec: int = 10, repeat_limit: int = 3):
        self.max_msgs = max_msgs
        self.window_sec = window_sec
        self.repeat_limit = repeat_limit
        self._times: dict[int, list[float]] = {}
        self._recent: dict[int, list[str]] = {}

    def check(self, user_id: int, text: str, now: float | None = None) -> str | None:
        """Returns a reason string if flooding, else None."""
        now = now if now is not None else time.monotonic()

        times = [t for t in self._times.get(user_id, []) if now - t < self.window_sec]
        times.append(now)
        self._times[user_id] = times
        if len(times) > self.max_msgs:
            return f"flood: {len(times)} msgs/{self.window_sec}s"

        norm = text.strip().lower()
        recent = self._recent.get(user_id, [])
        recent.append(norm)
        recent = recent[-self.repeat_limit:]
        self._recent[user_id] = recent
        if len(recent) == self.repeat_limit and len(set(recent)) == 1 and norm:
            return "repeated identical message"

        return None


class WarningTracker:
    """Counts spam offenses per user to escalate (warn -> mute)."""

    def __init__(self):
        self._counts: dict[int, int] = {}

    def add(self, user_id: int) -> int:
        self._counts[user_id] = self._counts.get(user_id, 0) + 1
        return self._counts[user_id]

    def get(self, user_id: int) -> int:
        return self._counts.get(user_id, 0)
