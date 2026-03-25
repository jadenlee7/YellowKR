"""
Yellow Korea knowledge base and AI chat handler.
Provides information about Yellow protocol/project to users.
"""

import logging
from openai import AsyncOpenAI

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Core knowledge about Yellow (can be extended)
YELLOW_INFO = {
    "about": (
        "Yellow은 크로스체인 거래를 가능하게 하는 탈중앙화 브로커 클리어링 네트워크입니다. "
        "Yellow Network는 state channel 기술을 활용하여 다양한 블록체인과 거래소 간의 "
        "고속, 저비용 거래를 지원합니다."
    ),
    "features": (
        "- State Channel 기반 고속 거래\n"
        "- 크로스체인 브로커 클리어링\n"
        "- 탈중앙화 거래소 인프라\n"
        "- 다중 체인 지원\n"
        "- 기관급 거래 성능"
    ),
    "token": (
        "YELLOW 토큰은 Yellow Network의 네이티브 토큰으로, "
        "네트워크 참여, 스테이킹, 거버넌스에 사용됩니다."
    ),
    "links": (
        "공식 채널:\n"
        "- Twitter/X: https://x.com/Yellow__Korea\n"
        "- Telegram 공지방: https://t.me/YellowKorea_ann\n"
        "- Yellow Network: https://www.yellow.org"
    ),
    "community": (
        "Yellow Korea 커뮤니티는 한국어 사용자를 위한 "
        "Yellow Network의 공식 한국 커뮤니티입니다. "
        "최신 뉴스, 업데이트, 이벤트 정보를 한국어로 제공합니다."
    ),
}

SYSTEM_PROMPT = """당신은 Yellow Korea 공식 텔레그램 봇입니다.
Yellow Network에 대한 정보를 한국어로 친절하게 제공합니다.

핵심 정보:
{about}

주요 기능:
{features}

토큰 정보:
{token}

공식 링크:
{links}

커뮤니티:
{community}

규칙:
1. Yellow Network에 대한 질문에 정확하고 친절하게 답변하세요.
2. 모르는 정보는 공식 채널을 안내하세요.
3. 투자 조언은 하지 마세요. 항상 DYOR(Do Your Own Research)를 권장하세요.
4. 한국어로 대화하되, 영어 질문에는 영어로 답변하세요.
5. 스캠/피싱 링크에 대해 경고하세요.
6. Yellow Korea 공지방(https://t.me/YellowKorea_ann)과 트위터(https://x.com/Yellow__Korea)를 자주 안내하세요.
""".format(**YELLOW_INFO)


# Keyword-based responses for when OpenAI is not available
KEYWORD_RESPONSES = {
    ("yellow", "옐로우", "옐로", "뭐", "소개", "무엇", "what"): YELLOW_INFO["about"],
    ("기능", "특징", "feature"): YELLOW_INFO["features"],
    ("토큰", "코인", "token", "coin", "$yellow"): YELLOW_INFO["token"],
    ("링크", "사이트", "link", "website", "홈페이지", "공식"): YELLOW_INFO["links"],
    ("커뮤니티", "community", "한국", "korea"): YELLOW_INFO["community"],
    ("스테이킹", "staking", "stake"): (
        "Yellow 토큰 스테이킹에 대한 최신 정보는 "
        "공식 채널을 확인해주세요:\n"
        "- https://x.com/Yellow__Korea\n"
        "- https://t.me/YellowKorea_ann"
    ),
    ("가격", "price", "시세", "얼마"): (
        "토큰 가격에 대한 실시간 정보는 공식 거래소를 확인해주세요. "
        "투자는 항상 본인의 판단으로 진행해주세요. DYOR!"
    ),
    ("안녕", "하이", "hello", "hi", "반가"): (
        "안녕하세요! Yellow Korea 봇입니다. "
        "Yellow에 대해 궁금한 점이 있으시면 편하게 질문해주세요! "
    ),
    ("도움", "help", "명령어", "command"): (
        "사용 가능한 명령어:\n"
        "/start - 봇 시작 & 소개\n"
        "/about - Yellow 소개\n"
        "/links - 공식 링크\n"
        "/subscribe - 트윗 알림 구독\n"
        "/unsubscribe - 트윗 알림 해제\n"
        "/latest - 최근 트윗 보기\n\n"
        "또는 자유롭게 Yellow에 대해 질문해주세요!"
    ),
}


class YellowChatHandler:
    """Handles user chat messages about Yellow."""

    def __init__(self):
        self.openai_client = None
        if OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            logger.info("OpenAI client initialized for AI chat")
        else:
            logger.info("No OpenAI key. Using keyword-based responses.")

    async def get_response(self, user_message: str) -> str:
        """Generate a response to a user message about Yellow."""
        if self.openai_client:
            return await self._ai_response(user_message)
        return self._keyword_response(user_message)

    async def _ai_response(self, user_message: str) -> str:
        """Generate AI-powered response using OpenAI."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            return response.choices[0].message.content or self._keyword_response(
                user_message
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self._keyword_response(user_message)

    def _keyword_response(self, user_message: str) -> str:
        """Generate response based on keyword matching."""
        message_lower = user_message.lower()

        for keywords, response in KEYWORD_RESPONSES.items():
            if any(kw in message_lower for kw in keywords):
                return response

        return (
            "Yellow에 대해 궁금한 점이 있으시면 편하게 질문해주세요!\n\n"
            "명령어 목록은 /help 를 입력해주세요.\n"
            "최신 소식은 공식 채널을 확인해주세요:\n"
            "- Twitter: https://x.com/Yellow__Korea\n"
            "- 공지방: https://t.me/YellowKorea_ann"
        )
