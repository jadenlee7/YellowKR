"""
Yellow Korea knowledge base and Claude AI chat handler.
Provides information about Yellow protocol/project to users.
"""

import logging
import random
import anthropic

from src.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Core knowledge about Yellow
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
        "- Telegram 채팅방: https://t.me/YellowKorea_chat\n"
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
7. 대화 톤은 친근하고 프로페셔널하게 유지하세요.
8. 답변은 간결하되 핵심 정보를 빠짐없이 전달하세요.

중요 포맷 규칙:
- 응답은 텔레그램 HTML 형식으로 작성하세요.
- 볼드체는 반드시 <b>텍스트</b> 태그를 사용하세요. **텍스트** 마크다운을 절대 사용하지 마세요.
- 이탤릭은 <i>텍스트</i> 태그를 사용하세요.
- 코드는 <code>텍스트</code> 태그를 사용하세요.
- 링크는 그대로 텍스트로 보내세요 (HTML <a> 태그 사용하지 마세요).
- &, <, > 문자를 일반 텍스트로 쓸 때는 &amp; &lt; &gt; 로 이스케이프하세요.
""".format(**YELLOW_INFO)


# Keyword-based responses (fallback when no API key)
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
        "안녕하세요! Yellow Korea 봇입니다.\n"
        "Yellow에 대해 궁금한 점이 있으시면 편하게 질문해주세요!"
    ),
    ("도움", "help", "명령어", "command"): (
        "사용 가능한 명령어:\n"
        "/start - 봇 시작 & 소개\n"
        "/about - Yellow 소개\n"
        "/links - 공식 링크\n"
        "/subscribe - 알림 구독\n"
        "/unsubscribe - 알림 해제\n"
        "/latest - 최근 공지/트윗 보기\n"
        "/tip - Yellow 팁 받기\n\n"
        "또는 자유롭게 Yellow에 대해 질문해주세요!"
    ),
}


# Auto-engagement tips
YELLOW_TIPS = [
    (
        "<b>Yellow Tip</b>\n\n"
        "Yellow Network의 State Channel 기술은 오프체인에서 거래를 처리하여 "
        "가스비를 절감하고 속도를 높입니다.\n\n"
        "자세히: https://t.me/YellowKorea_ann"
    ),
    (
        "<b>알고 계셨나요?</b>\n\n"
        "Yellow Network는 다양한 거래소와 블록체인을 하나로 연결하여 "
        "유동성 분산 문제를 해결합니다.\n\n"
        "공식 채널: https://t.me/YellowKorea_ann"
    ),
    (
        "<b>Yellow 101</b>\n\n"
        "크로스체인 브로커 클리어링이란? 서로 다른 체인의 자산을 "
        "중개 없이 안전하게 교환할 수 있는 기술입니다.\n\n"
        "더 알아보기: https://www.yellow.org"
    ),
    (
        "<b>Yellow Network Update</b>\n\n"
        "Yellow Korea 공지방에서 최신 업데이트를 확인하세요!\n"
        "https://t.me/YellowKorea_ann\n\n"
        "Twitter: https://x.com/Yellow__Korea"
    ),
    (
        "<b>Yellow Community</b>\n\n"
        "Yellow Korea 커뮤니티에 참여하세요! "
        "함께 Yellow Network의 성장을 만들어갑니다.\n\n"
        "채팅방: https://t.me/YellowKorea_chat\n"
        "공지방: https://t.me/YellowKorea_ann"
    ),
    (
        "<b>Yellow Tip</b>\n\n"
        "YELLOW 토큰은 네트워크 보안, 스테이킹, 거버넌스에 활용됩니다. "
        "토큰 홀더는 네트워크 의사결정에 참여할 수 있습니다.\n\n"
        "DYOR: https://www.yellow.org"
    ),
    (
        "<b>알고 계셨나요?</b>\n\n"
        "Yellow Network는 기관급 성능을 제공하면서도 "
        "탈중앙화를 유지합니다. 중앙 서버 없이 P2P로 동작합니다.\n\n"
        "자세히: https://t.me/YellowKorea_ann"
    ),
]


def get_random_tip() -> str:
    """Get a random Yellow tip for auto-engagement."""
    return random.choice(YELLOW_TIPS)


class YellowChatHandler:
    """Handles user chat messages about Yellow using Claude API."""

    def __init__(self):
        self.client = None
        if ANTHROPIC_API_KEY:
            self.client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
            logger.info("Anthropic Claude client initialized for AI chat")
        else:
            logger.info("No Anthropic API key. Using keyword-based responses.")

    async def get_response(self, user_message: str, user_name: str = "") -> str:
        """Generate a response to a user message about Yellow."""
        if self.client:
            return await self._claude_response(user_message, user_name)
        return self._keyword_response(user_message)

    async def _claude_response(self, user_message: str, user_name: str = "") -> str:
        """Generate AI-powered response using Claude."""
        try:
            user_context = f"[유저: {user_name}] " if user_name else ""
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": f"{user_context}{user_message}"},
                ],
            )
            text = response.content[0].text if response.content else None
            return text or self._keyword_response(user_message)
        except Exception as e:
            logger.error(f"Claude API error: {e}")
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
