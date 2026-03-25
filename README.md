# Yellow Korea Bot

Yellow Network 한국 커뮤니티를 위한 텔레그램 봇입니다.

## 기능

- **트위터 스크래핑**: `@Yellow__Korea` 트윗 → 구독자 자동 전달 (Nitter RSS)
- **AI 챗봇**: Claude AI로 유저와 대화하며 Yellow 정보 전달
- **자동 팁 발송**: 정기적으로 Yellow 관련 팁/정보 자동 전송
- **자동 구독**: `/start` 시 자동으로 알림 구독

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 (자동 구독) |
| `/about` | Yellow Network 소개 |
| `/links` | 공식 링크 모음 |
| `/subscribe` | 트윗 알림 구독 |
| `/unsubscribe` | 트윗 알림 해제 |
| `/latest` | 최근 트윗 보기 |
| `/tip` | Yellow 팁 받기 |
| `/help` | 도움말 |

## Railway 배포

Railway Dashboard에서 환경 변수 설정:

| 변수 | 설명 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | @BotFather 발급 토큰 |
| `ANTHROPIC_API_KEY` | Anthropic Claude API 키 |
| `TWITTER_USERNAME` | 스크래핑할 트위터 계정 (기본: Yellow__Korea) |

## 로컬 실행

```bash
cp .env.example .env
pip install -r requirements.txt
python main.py
```

## 자동화

| 기능 | 주기 |
|------|------|
| 트윗 스크래핑 | 5분 |
| Yellow 팁 | 60분 |
| AI 대화 | 실시간 |

## 공식 채널

- Twitter/X: https://x.com/Yellow__Korea
- Telegram 공지방: https://t.me/YellowKorea_ann
- Telegram 채팅방: https://t.me/YellowKorea_chat
