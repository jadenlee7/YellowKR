# Yellow Korea Bot

Yellow Network 한국 커뮤니티를 위한 텔레그램 봇입니다.

## 기능

- **공지방 스크래핑**: `@YellowKorea_ann` 텔레그램 채널 새 글 → 구독자 자동 전달
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
| `/subscribe` | 알림 구독 |
| `/unsubscribe` | 알림 해제 |
| `/latest` | 최근 공지 + 트윗 보기 |
| `/tip` | Yellow 팁 받기 |
| `/help` | 도움말 |

## Railway 배포

### 1. 환경 변수 설정 (Railway Dashboard)

| 변수 | 설명 |
|------|------|
| `TELEGRAM_BOT_TOKEN` | @BotFather 발급 토큰 |
| `ANTHROPIC_API_KEY` | Anthropic Claude API 키 |
| `TELEGRAM_API_ID` | my.telegram.org 앱 ID |
| `TELEGRAM_API_HASH` | my.telegram.org 앱 해시 |
| `TELEGRAM_PHONE` | Telethon 인증용 전화번호 |

### 2. 배포

```bash
# Railway CLI
railway up

# 또는 GitHub 연동으로 자동 배포
```

## 로컬 실행

```bash
cp .env.example .env
# .env 편집
pip install -r requirements.txt
python main.py
```

## 자동화

| 기능 | 주기 | 설명 |
|------|------|------|
| 채널 스크래핑 | 3분 | `@YellowKorea_ann` 새 글 감지 |
| 트윗 스크래핑 | 5분 | `@Yellow__Korea` 새 트윗 감지 |
| Yellow 팁 | 60분 | 랜덤 Yellow 정보 자동 발송 |
| AI 대화 | 실시간 | 모든 메시지에 Claude AI 응답 |

## 구조

```
YellowKR/
├── main.py                   # 진입점
├── src/
│   ├── bot.py                # 텔레그램 봇 + 스케줄러
│   ├── config.py             # 환경 변수
│   ├── subscribers.py        # 구독자 관리
│   ├── telegram_scraper.py   # 텔레그램 채널 스크래퍼
│   ├── twitter_scraper.py    # 트위터 스크래퍼 (Nitter)
│   └── yellow_knowledge.py   # Yellow 지식 + Claude AI 챗
├── Procfile                  # Railway worker
├── railway.json              # Railway 설정
├── nixpacks.toml             # Railway 빌드
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 공식 채널

- Twitter/X: https://x.com/Yellow__Korea
- Telegram 공지방: https://t.me/YellowKorea_ann
- Telegram 채팅방: https://t.me/YellowKorea_chat
