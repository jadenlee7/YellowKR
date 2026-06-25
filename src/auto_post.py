"""
Auto-posting scheduler for Yellow Korea chat.
Posts @yellow tweets + crypto engagement content every 30 min (8AM-11PM KST).
Filters out Yellow Pro content.
"""

import logging
import os
import random
from datetime import datetime, timezone, timedelta

import anthropic

from src.config import (
    ANTHROPIC_API_KEY,
    TWITTER_MAIN_USERNAME,
    DATA_DIR,
    LAST_MAIN_TWEET_FILE,
)

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

# Yellow Pro 필터 키워드
YELLOW_PRO_FILTER = [
    "yellow pro",
    "yellowpro",
    "pro plan",
    "pro tier",
    "upgrade to pro",
    "pro subscription",
    "pro feature",
]


def is_within_posting_hours() -> bool:
    """Check if current time is within 8AM-11PM KST."""
    now_kst = datetime.now(KST)
    return 8 <= now_kst.hour < 23


def is_yellow_pro_content(text: str) -> bool:
    """Filter out Yellow Pro related content."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in YELLOW_PRO_FILTER)


def get_last_main_tweet_id() -> str | None:
    try:
        if os.path.exists(LAST_MAIN_TWEET_FILE):
            with open(LAST_MAIN_TWEET_FILE, "r") as f:
                val = f.read().strip()
                return val if val else None
    except Exception as e:
        logger.error(f"Error reading last main tweet ID: {e}")
    return None


def save_last_main_tweet_id(tweet_id: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LAST_MAIN_TWEET_FILE, "w") as f:
        f.write(str(tweet_id))


# Engagement post templates - encourage conversation
ENGAGEMENT_TEMPLATES = [
    # Crypto market discussion
    (
        "오늘 크립토 시장 어떻게 보세요? 🤔\n\n"
        "최근 크로스체인 쪽 움직임이 심상치 않은데,\n"
        "여러분은 어떤 섹터에 관심 있으세요?"
    ),
    (
        "주말 포트폴리오 점검 하셨나요?\n\n"
        "요즘 DeFi 쪽에서 어떤 프로젝트가 눈에 띄나요?\n"
        "자유롭게 이야기해봐요 💬"
    ),
    (
        "크립토 시장에서 가장 중요하게 보는 지표가 뭔가요?\n\n"
        "TVL? 거래량? 아니면 다른 거?\n"
        "다들 어떻게 분석하시는지 궁금해요"
    ),
    # Yellow specific engagement
    (
        "Yellow Network 최근 업데이트 확인하셨나요?\n\n"
        "@yellow 트위터에서 새 소식이 올라왔어요.\n"
        "어떻게 생각하시나요? 👀"
    ),
    (
        "크로스체인 거래의 미래, 어떻게 보세요?\n\n"
        "State Channel vs 브릿지 vs 기타 솔루션...\n"
        "여러분의 생각은?"
    ),
    (
        "오늘도 Yellow Korea 커뮤니티에서 활발한 대화 나눠봐요!\n\n"
        "Yellow Network이든 크립토 전반이든\n"
        "궁금한 거 있으면 편하게 물어보세요 🙌"
    ),
    # General crypto topics
    (
        "이번 주 크립토 뉴스 중 가장 인상적인 거 뭐였나요?\n\n"
        "다들 어떤 뉴스에 주목하고 있는지 공유해봐요 📰"
    ),
    (
        "탈중앙화 거래소 vs 중앙화 거래소\n\n"
        "여러분은 어디서 주로 거래하시나요?\n"
        "각각 장단점이 있죠"
    ),
    (
        "크립토 입문자에게 가장 먼저 추천하고 싶은 게 뭔가요?\n\n"
        "처음 시작할 때 알았으면 좋았을 것들 공유해봐요"
    ),
    (
        "Layer 1 vs Layer 2, 어디에 더 주목하고 있나요?\n\n"
        "확장성 문제 해결 방법에 대해 얘기해봐요 🔗"
    ),
    # Yellow ecosystem
    (
        "Yellow Network의 State Channel 기술에 대해 어떻게 생각하세요?\n\n"
        "오프체인 거래 처리 방식이 가스비 문제를\n"
        "해결할 수 있을까요? 의견 남겨주세요!"
    ),
    (
        "브로커 클리어링 네트워크가 왜 필요할까요?\n\n"
        "기존 거래소 시스템의 문제점과\n"
        "Yellow의 접근 방식에 대해 이야기해봐요"
    ),
]


def get_engagement_post() -> str:
    """Get a random engagement post."""
    return random.choice(ENGAGEMENT_TEMPLATES)


async def generate_tweet_discussion(tweet_text: str) -> str | None:
    """Use Claude to generate a discussion prompt from a @yellow tweet."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=(
                "당신은 Yellow Korea 텔레그램 커뮤니티 봇입니다. "
                "@yellow 트위터의 트윗을 보고, 커뮤니티 유저들이 대화할 수 있도록 "
                "자연스러운 토론 주제로 바꿔주세요. "
                "짧고 친근하게 작성하고, 유저들의 의견을 물어보세요. "
                "HTML 포맷 사용: <b>볼드</b>, **마크다운** 금지. "
                "링크는 붙이지 마세요."
            ),
            messages=[
                {"role": "user", "content": f"이 트윗을 커뮤니티 토론 주제로 바꿔줘:\n\n{tweet_text}"},
            ],
        )
        return response.content[0].text if response.content else None
    except Exception as e:
        logger.warning(f"Failed to generate tweet discussion: {e}")
        return None


def format_yellow_main_tweet(tweet: dict) -> str:
    """Format a @yellow tweet for the chat group."""
    text = tweet["text"]
    if len(text) > 400:
        text = text[:400] + "..."

    return (
        f"<b>@yellow 새 소식</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 {tweet['url']}\n\n"
        f"이 소식에 대해 어떻게 생각하세요? 💬"
    )
