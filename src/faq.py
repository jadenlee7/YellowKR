"""
Auto-FAQ: detect frequently asked, simple questions and answer them with a
canned response instead of calling Claude. Cuts API cost and latency on the
high-volume "what is it / when listing / where to buy / price" questions while
letting nuanced or longer messages fall through to the AI handler.

A message is answered from the FAQ only when it is short (looks like a direct
question) AND matches one entry's keywords — so real conversation still reaches
Claude.
"""

# Only treat a message as an FAQ when it's this short or less (chars). Longer,
# more conversational messages go to Claude for a natural reply.
FAQ_MAX_LEN = 25

# If the message signals it wants opinion/analysis/explanation, skip the canned
# answer and let Claude handle it — even if it's short and matches a keyword.
FAQ_EXCLUDE = (
    "생각", "어때", "장단점", "비교", "왜", "설명", "자세", "분석", "의견",
    "전망", "예상", "추천해", "어떻게 봐", "어떤가",
)

# Each entry: trigger keywords (lowercased substring match) + canned answer.
# Ordered most-specific first so e.g. "상장" wins before a generic "yellow".
FAQ_ENTRIES = [
    {
        "keywords": ("상장", "listing", "리스팅", "언제 상장", "상장일"),
        "answer": (
            "상장 관련 공식 발표는 아래 채널에서 가장 먼저 확인할 수 있어요.\n"
            "- 공지방: https://t.me/YellowKorea_ann\n"
            "- Twitter: https://x.com/yellow\n"
            "확정되지 않은 정보는 루머일 수 있으니 공식 채널을 기준으로 봐주세요!"
        ),
    },
    {
        "keywords": ("에어드랍", "에어드롭", "airdrop", "에어드람"),
        "answer": (
            "에어드랍/이벤트 정보는 공식 채널에서만 공지돼요.\n"
            "- 공지방: https://t.me/YellowKorea_ann\n"
            "DM으로 '에어드랍 받으세요' 같은 메시지는 100% 스캠이니 절대 지갑을 연결하지 마세요!"
        ),
    },
    {
        "keywords": ("스테이킹", "staking", "stake"),
        "answer": (
            "YELLOW 토큰 스테이킹/거버넌스 관련 최신 안내는 공지방에서 확인할 수 있어요.\n"
            "https://t.me/YellowKorea_ann"
        ),
    },
    {
        "keywords": ("어디서 사", "어디서 구매", "어디서 살", "where to buy", "거래소 어디", "구매 방법"),
        "answer": (
            "거래 가능한 거래소 정보는 공식 채널에서 확인하는 게 가장 정확해요.\n"
            "- 공식 사이트: https://www.yellow.org\n"
            "- 공지방: https://t.me/YellowKorea_ann\n"
            "투자는 본인 판단으로! DYOR 🙏"
        ),
    },
    {
        "keywords": ("가격", "시세", "price", "얼마", "몇 원", "몇 달러"),
        "answer": (
            "실시간 가격은 거래소나 코인마켓캡 등에서 직접 확인하는 게 정확해요. "
            "투자는 본인 판단으로, DYOR!"
        ),
    },
    {
        "keywords": ("로드맵", "roadmap", "계획"),
        "answer": (
            "로드맵과 개발 현황은 공식 사이트와 트위터에서 확인할 수 있어요.\n"
            "- https://www.yellow.org\n"
            "- https://x.com/yellow"
        ),
    },
    {
        "keywords": ("백서", "whitepaper", "white paper", "docs", "문서"),
        "answer": (
            "백서/공식 문서는 여기서 볼 수 있어요: https://www.yellow.org"
        ),
    },
    {
        "keywords": ("공식 링크", "공식 채널", "링크 어디", "사이트 어디", "official link"),
        "answer": (
            "<b>Yellow 공식 채널</b>\n"
            "- 사이트: https://www.yellow.org\n"
            "- Twitter(글로벌): https://x.com/yellow\n"
            "- Twitter(한국): https://x.com/Yellow__Korea\n"
            "- 공지방: https://t.me/YellowKorea_ann\n"
            "- 채팅방: https://t.me/YellowKorea_chat"
        ),
    },
    {
        "keywords": ("yellow이 뭐", "yellow가 뭐", "옐로우가 뭐", "옐로우 뭐", "뭐하는", "what is yellow", "뭔 프로젝트"),
        "answer": (
            "Yellow는 state channel 기술로 여러 블록체인·거래소를 잇는 "
            "탈중앙화 브로커 클리어링 네트워크예요. 크로스체인 거래를 빠르고 저렴하게 "
            "처리하는 게 핵심이에요. 자세히: https://www.yellow.org"
        ),
    },
]


def match_faq(text: str) -> str | None:
    """Return a canned FAQ answer for a short, FAQ-shaped message, else None."""
    if not text:
        return None
    stripped = text.strip()
    if len(stripped) > FAQ_MAX_LEN:
        return None
    low = stripped.lower()
    if any(x in low for x in FAQ_EXCLUDE):
        return None
    for entry in FAQ_ENTRIES:
        if any(kw in low for kw in entry["keywords"]):
            return entry["answer"]
    return None
