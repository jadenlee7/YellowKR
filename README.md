# Yellow Korea Bot

Yellow Network 한국 커뮤니티를 위한 텔레그램 봇입니다.

## 기능

- **공지방 실시간 스크래핑**: `@YellowKorea_ann` 텔레그램 채널의 새 글을 자동 감지하여 구독자에게 전달
- **Yellow 정보 제공**: Yellow Network에 대한 정보를 한국어로 제공
- **대화형 챗봇**: 유저들과 대화하며 Yellow에 대한 정보를 전달 (AI/키워드 기반)
- **자동 팁 발송**: 정기적으로 Yellow 관련 팁/정보를 구독자에게 자동 전송
- **자동 구독**: `/start` 시 자동으로 알림 구독

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 & 소개 (자동 구독) |
| `/about` | Yellow Network 소개 |
| `/links` | 공식 링크 모음 |
| `/subscribe` | 공지 알림 구독 |
| `/unsubscribe` | 공지 알림 해제 |
| `/latest` | 최근 공지 보기 |
| `/tip` | Yellow 팁 받기 |
| `/help` | 도움말 |

자유 텍스트 입력 시 Yellow 관련 정보로 자동 응답합니다.

## 설치 & 실행

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 토큰 입력
```

필수:
- `TELEGRAM_BOT_TOKEN`: [@BotFather](https://t.me/BotFather)에서 발급
- `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`: [my.telegram.org/apps](https://my.telegram.org/apps)에서 발급
- `TELEGRAM_PHONE`: Telethon 세션용 전화번호

선택:
- `OPENAI_API_KEY`: AI 챗봇 기능 (없으면 키워드 기반 응답)

### 2. 직접 실행

```bash
pip install -r requirements.txt
python main.py
```

첫 실행 시 Telethon 인증 코드를 입력해야 합니다 (이후 세션 유지).

### 3. Docker 실행

```bash
docker-compose up -d
```

## 자동화 기능

| 기능 | 주기 | 설명 |
|------|------|------|
| 채널 스크래핑 | 3분 | `@YellowKorea_ann` 새 글 감지 → 구독자 전송 |
| Yellow 팁 | 60분 | 랜덤 Yellow 정보/팁 → 구독자 전송 |
| 자동 구독 | `/start` 시 | 새 유저 자동 알림 구독 |
| 유저 대화 | 실시간 | 모든 메시지에 Yellow 관련 정보로 응답 |

## 프로젝트 구조

```
YellowKR/
├── main.py                   # 메인 진입점
├── src/
│   ├── bot.py                # 텔레그램 봇 핸들러 + 스케줄러
│   ├── config.py             # 환경 변수 설정
│   ├── subscribers.py        # 구독자 관리
│   ├── telegram_scraper.py   # 텔레그램 채널 스크래퍼 (Telethon)
│   └── yellow_knowledge.py   # Yellow 정보 & AI 챗 & 자동 팁
├── data/                     # 런타임 데이터
│   ├── subscribers.json      # 구독자 목록
│   ├── last_channel_msg_id.txt
│   └── sessions/             # Telethon 세션 파일
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 공식 채널

- Twitter/X: https://x.com/Yellow__Korea
- Telegram 공지방: https://t.me/YellowKorea_ann
