# Yellow Korea Bot

Yellow Network 한국 커뮤니티를 위한 텔레그램 봇입니다.

## 기능

- **트윗 실시간 알림**: `@Yellow__Korea` 트위터 계정의 새 트윗을 자동으로 감지하여 구독자에게 전달
- **Yellow 정보 제공**: Yellow Network에 대한 정보를 한국어로 제공
- **대화형 챗봇**: 유저들과 대화하며 Yellow에 대한 정보를 전달
- **공지방 연동**: [Yellow Korea 공지방](https://t.me/YellowKorea_ann) 정보 참고 안내

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 & 소개 |
| `/about` | Yellow Network 소개 |
| `/links` | 공식 링크 모음 |
| `/subscribe` | 트윗 알림 구독 |
| `/unsubscribe` | 트윗 알림 해제 |
| `/latest` | 최근 트윗 보기 |
| `/help` | 도움말 |

## 설치 & 실행

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 토큰 입력
```

필수:
- `TELEGRAM_BOT_TOKEN`: [@BotFather](https://t.me/BotFather)에서 발급
- `TWITTER_BEARER_TOKEN`: [Twitter Developer Portal](https://developer.twitter.com)에서 발급

선택:
- `OPENAI_API_KEY`: AI 챗봇 기능 (없으면 키워드 기반 응답)

### 2. 직접 실행

```bash
pip install -r requirements.txt
python main.py
```

### 3. Docker 실행

```bash
docker-compose up -d
```

## 프로젝트 구조

```
YellowKR/
├── main.py                # 메인 진입점
├── src/
│   ├── bot.py             # 텔레그램 봇 핸들러
│   ├── config.py          # 환경 변수 설정
│   ├── subscribers.py     # 구독자 관리
│   ├── twitter_scraper.py # 트위터 스크래퍼
│   └── yellow_knowledge.py # Yellow 정보 & AI 챗
├── data/                  # 런타임 데이터 (구독자, 마지막 트윗 ID)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 공식 채널

- Twitter/X: https://x.com/Yellow__Korea
- Telegram 공지방: https://t.me/YellowKorea_ann
