# Yellow Korea Bot

Yellow Network 한국 커뮤니티를 위한 텔레그램 봇입니다.

## 기능

- **신규 입장자 캡차**: 새 멤버는 입장 시 자동으로 뮤트되고, 인증 버튼을 눌러야
  발언 가능 (제한 시간 내 미인증 시 자동 추방) — 대량 스팸봇 침투 차단
- **스팸 방지**: 에어드랍/피싱/사칭/도배/대량 멘션 등을 점수 기반으로 탐지해
  삭제·경고하고, 반복 위반자는 일정 시간 뮤트 (그룹 관리자 권한 필요)
- **Yellow 관련 메시지만 답장**: 그룹·DM 모두 Yellow 관련 내용·봇 멘션·봇 답글에만
  반응 (모든 메시지에 답하지 않아 채팅방이 깔끔)
- **자동 FAQ**: 자주 나오는 짧은 질문(상장/가격/에어드랍/구매처 등)은 미리 만든
  답변으로 즉시 응대 → Claude 호출 비용·지연 절감 (긴/심화 질문은 AI로)
- **리더보드 & 리포트**: 멤버별 활동량·화제 키워드·유저 질문·스팸 차단·FAQ 응답 수를
  집계해 매일(오전 9시) + 매주(월요일) 운영자에게 개인 DM 요약 (Claude가 다음
  콘텐츠 방향도 제안)
- **간간히 정보 제공**: 자동 정보 포스팅은 하루 2~3회로 제한하고, 사람들이 실제로
  대화 중일 때만 발송 (봇이 혼자 떠드는 상황 방지)
- **트위터 스크래핑**: `@yellow` + `@Yellow__Korea` 트윗 → 채팅방/구독자 자동 전달
- **AI 챗봇**: Claude AI (Opus 4.8) 로 Yellow 정보 제공

## 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 봇 시작 (자동 구독) |
| `/about` | Yellow Network 소개 |
| `/links` | 공식 링크 모음 |
| `/subscribe` | 트윗 알림 구독 |
| `/unsubscribe` | 트윗 알림 해제 |
| `/latest` | 최근 트윗 보기 |
| `/top` | 활동 리더보드 (오늘) |
| `/help` | 도움말 |
| `/myid` | 내 텔레그램 ID 확인 |
| `/stats` | 오늘 통계 (운영자) |
| `/report` | 활동 요약 DM (운영자) |

## 운영자 설정

데일리 요약 DM을 받으려면 운영자 ID를 등록해야 합니다.

1. 봇에게 1:1(개인 채팅)로 `/myid` 전송 → 본인 텔레그램 숫자 ID 확인
2. 환경 변수 `OWNER_TELEGRAM_ID` 에 그 값 설정
3. 봇이 그룹에서 메시지 삭제/뮤트를 하려면 **그룹 관리자**로 추가하고
   "메시지 삭제"·"사용자 제한" 권한을 부여하세요.

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
| 자동 정보 포스팅 | 하루 2~3회 (활동 시에만) |
| 데일리 리포트 DM | 매일 오전 9시 (KST) |
| 주간 리포트 DM | 매주 월요일 오전 9시 (KST) |
| 캡차 / 스팸 / FAQ / AI 대화 | 실시간 |

> 활동 데이터(`data/stats.json`)는 컨테이너 재시작 시 사라지므로, Railway에서는
> `data/` 경로에 볼륨을 마운트하면 리더보드가 누적 유지됩니다.

## 공식 채널

- Twitter/X: https://x.com/Yellow__Korea
- Telegram 공지방: https://t.me/YellowKorea_ann
- Telegram 채팅방: https://t.me/YellowKorea_chat
