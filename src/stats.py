"""
Chat activity tracking: per-user leaderboards, daily message stats,
topic/question collection, and auto-post gating state.

All data persists to a single JSON file (config.STATS_FILE). Old daily buckets
are pruned so the file stays small.
"""

import json
import logging
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from src.config import STATS_FILE, DATA_DIR

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# Keep this many days of daily history.
DAILY_RETENTION_DAYS = 14

# Words ignored when extracting discussion topics (Korean + English filler).
STOPWORDS = {
    "the", "and", "for", "you", "are", "with", "this", "that", "but", "not",
    "have", "was", "your", "can", "all", "about", "한테", "그게", "근데", "진짜",
    "이거", "저거", "그거", "오늘", "지금", "그냥", "정말", "너무", "그리고",
    "하는", "하고", "있는", "있어", "없어", "같아", "같은", "해서", "되는",
    "그래", "그럼", "여기", "거기", "우리", "저는", "제가", "님은", "에서",
    "으로", "하면", "면서", "라고", "다고", "어요", "네요", "지만", "는데",
    "ㅋㅋ", "ㅎㅎ", "ㅋㅋㅋ", "ㅎㅎㅎ", "ㅇㅇ", "ㄴㄴ", "넵", "넹", "옙",
}

_TOKEN_RE = re.compile(r"[A-Za-z가-힣\$]{2,}")


def _today_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(KST).isoformat()


class StatsManager:
    """Tracks chat activity and persists it to disk."""

    def __init__(self):
        self.data = self._load()

    # ── persistence ──

    def _load(self) -> dict:
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading stats: {e}")
        return {"users": {}, "daily": {}, "chat_state": {}}

    def _save(self) -> None:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving stats: {e}")

    def _day(self, date_str: str | None = None) -> dict:
        date_str = date_str or _today_str()
        daily = self.data.setdefault("daily", {})
        if date_str not in daily:
            daily[date_str] = {
                "messages": 0,
                "spam_removed": 0,
                "new_members": 0,
                "active_users": {},   # user_id -> count
                "questions": [],
                "keywords": {},       # word -> count
            }
            self._prune_daily()
        return daily[date_str]

    def _prune_daily(self) -> None:
        daily = self.data.get("daily", {})
        if len(daily) <= DAILY_RETENTION_DAYS:
            return
        for old in sorted(daily.keys())[:-DAILY_RETENTION_DAYS]:
            daily.pop(old, None)

    # ── recording ──

    def record_message(self, chat_id: int, user, text: str) -> None:
        """Record one human message for stats + leaderboard + post gating."""
        if user is None:
            return
        uid = str(user.id)

        # Lifetime per-user tally (the leaderboard).
        users = self.data.setdefault("users", {})
        entry = users.setdefault(uid, {"total": 0})
        entry["total"] = entry.get("total", 0) + 1
        entry["name"] = (user.first_name or "")[:40]
        entry["username"] = user.username or ""
        entry["last_active"] = _now_iso()

        # Today's bucket.
        day = self._day()
        day["messages"] += 1
        day["active_users"][uid] = day["active_users"].get(uid, 0) + 1

        # Collect questions (what people want to know).
        stripped = text.strip()
        if "?" in stripped and 4 <= len(stripped) <= 200:
            qs = day["questions"]
            if stripped not in qs:
                qs.append(stripped)
                day["questions"] = qs[-50:]

        # Topic keywords.
        kw = day["keywords"]
        for tok in self._tokens(text):
            kw[tok] = kw.get(tok, 0) + 1

        # Auto-post gating: a human just spoke.
        state = self._chat_state(chat_id)
        state["human_msgs_since_bot_post"] = state.get("human_msgs_since_bot_post", 0) + 1
        state["last_human_ts"] = _now_iso()

        self._save()

    def record_spam_removed(self, count: int = 1) -> None:
        self._day()["spam_removed"] += count
        self._save()

    def record_new_member(self, count: int = 1) -> None:
        self._day()["new_members"] += count
        self._save()

    @staticmethod
    def _tokens(text: str) -> list[str]:
        out = []
        for tok in _TOKEN_RE.findall(text.lower()):
            if tok in STOPWORDS or len(tok) < 2:
                continue
            out.append(tok)
        return out

    # ── auto-post gating ──

    def _chat_state(self, chat_id: int) -> dict:
        cs = self.data.setdefault("chat_state", {})
        return cs.setdefault(str(chat_id), {})

    def should_auto_post(self, chat_id: int, min_human_msgs: int, max_per_day: int) -> bool:
        """True only if humans have been active and the daily cap isn't hit."""
        state = self._chat_state(chat_id)
        today = _today_str()

        if state.get("post_count_date") != today:
            state["post_count_date"] = today
            state["posts_today"] = 0

        if state.get("posts_today", 0) >= max_per_day:
            return False
        if state.get("human_msgs_since_bot_post", 0) < min_human_msgs:
            return False
        return True

    def record_auto_post(self, chat_id: int) -> None:
        """Mark that the bot just auto-posted; resets the activity counter and
        counts toward the daily cap."""
        state = self._chat_state(chat_id)
        today = _today_str()
        if state.get("post_count_date") != today:
            state["post_count_date"] = today
            state["posts_today"] = 0
        state["posts_today"] = state.get("posts_today", 0) + 1
        state["human_msgs_since_bot_post"] = 0
        state["last_bot_post_ts"] = _now_iso()
        self._save()

    def note_bot_message(self, chat_id: int) -> None:
        """Reset the activity counter without counting toward the daily cap.
        Used for event-driven bot messages (e.g. relaying a new tweet) so an
        auto-post won't immediately follow and stack two bot messages."""
        state = self._chat_state(chat_id)
        state["human_msgs_since_bot_post"] = 0
        state["last_bot_post_ts"] = _now_iso()
        self._save()

    # ── reporting ──

    def get_leaderboard(self, date_str: str | None = None, n: int = 10) -> list[tuple[str, int]]:
        """Top active users for a given day (default today). Returns (label, count)."""
        day = self.data.get("daily", {}).get(date_str or _today_str())
        if not day:
            return []
        counts = day.get("active_users", {})
        users = self.data.get("users", {})
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
        out = []
        for uid, count in ranked:
            u = users.get(uid, {})
            label = u.get("username") and f"@{u['username']}" or u.get("name") or f"user{uid[-4:]}"
            out.append((label, count))
        return out

    def get_all_time_leaderboard(self, n: int = 10) -> list[tuple[str, int]]:
        users = self.data.get("users", {})
        ranked = sorted(users.items(), key=lambda kv: kv[1].get("total", 0), reverse=True)[:n]
        out = []
        for uid, u in ranked:
            label = u.get("username") and f"@{u['username']}" or u.get("name") or f"user{uid[-4:]}"
            out.append((label, u.get("total", 0)))
        return out

    def top_keywords(self, date_str: str | None = None, n: int = 8) -> list[tuple[str, int]]:
        day = self.data.get("daily", {}).get(date_str or _today_str())
        if not day:
            return []
        return Counter(day.get("keywords", {})).most_common(n)

    def get_questions(self, date_str: str | None = None, n: int = 10) -> list[str]:
        day = self.data.get("daily", {}).get(date_str or _today_str())
        if not day:
            return []
        return day.get("questions", [])[-n:]

    def day_summary(self, date_str: str | None = None) -> dict:
        date_str = date_str or _today_str()
        day = self.data.get("daily", {}).get(date_str, {})
        return {
            "date": date_str,
            "messages": day.get("messages", 0),
            "active_users": len(day.get("active_users", {})),
            "new_members": day.get("new_members", 0),
            "spam_removed": day.get("spam_removed", 0),
            "leaderboard": self.get_leaderboard(date_str),
            "keywords": self.top_keywords(date_str),
            "questions": self.get_questions(date_str),
        }
