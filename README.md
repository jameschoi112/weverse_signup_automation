# 위버스 계정 자동 생성기

위버스(Weverse) 계정을 자동으로 생성하는 Python 기반 도구입니다.
- *QA 환경 선택 시 @benx.com 메일 생성(인증 불가) , Real 환경 선택 시 실제 메일 수신 및 인증 자동처리 가능*
##  주요 기능

- **다중 환경 지원**: QA 테스트 환경과 실제 운영 환경 지원
- **Gmail 통합**: Gmail API를 통한 이메일 인증 자동 처리
- **Slack 알림**: 인증 과정은 슬랙에 특정 채널에서 별도로 진행
- **결과 저장**: 테스트 결과는 ID, PW, WID 출력 및 저장


##  프로젝트 구조

```
weverse_automation/
├── README.md
├── requirements.txt
├── setup.py
├── config/
│   ├── settings.py          # 전역 설정
│   └── credentials_template.json
├── src/
│   ├── models/
│   │   └── account.py       # 계정 데이터 모델
│   ├── services/
│   │   ├── email_generator.py    # 이메일 생성
│   │   ├── gmail_service.py      # Gmail API 연동
│   │   ├── slack_service.py      # Slack 알림
│   │   └── weverse_service.py    # 위버스 웹사이트 조작
│   ├── utils/
│   │   └── helpers.py       # 공통 유틸리티
│   └── core/
│       └── account_creator.py    # 메인 생성기
├── scripts/
│   ├── run_automation.py         # 메인 실행 스크립트
│   ├── create_single_account.py  # 단일 계정 생성
│   └── create_multiple_accounts.py # 다중 계정 생성
├── logs/
└── output/
```

## 🛠 설치 및 설정

### 1. 요구사항

- Python 3.8 이상
- Chrome/Chromium 브라우저

### 2. 패키지 설치

```bash
# 저장소 클론
git clone <repository-url>
cd weverse_signup_automation

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 3. Gmail API 설정 (선택사항)

Gmail 자동 인증을 사용하려면:

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Gmail API 활성화
3. OAuth 2.0 클라이언트 ID 생성
4. `credentials.json` 파일을 프로젝트 루트에 저장

### 4. Slack 웹훅 설정 (선택사항)

Slack 알림을 받으려면 Slack 웹훅 URL을 설정하세요. (미설정 시 default URL 설정)

##  사용법

- scripts/run_automation.py 를 수동으로 실행해도 됩니다.

### 메인 자동화 스크립트

```bash
# 대화형 모드로 실행
python scripts/run_automation.py --interactive



### 단일 계정 생성

```bash
# QA 환경에서 랜덤 계정 생성
python scripts/create_single_account.py --env qa

# Real 환경에서 Gmail 기반 계정 생성
python scripts/create_single_account.py --env real --base-email test@gmail.com

# 특정 이메일로 계정 생성 (QA 환경)
python scripts/create_single_account.py --env qa --email custom@benx.com
```

### 다중 계정 생성

```bash
# QA 환경에서 5개 계정 생성
python scripts/create_multiple_accounts.py --env qa --count 5

# 빠른 생성 (간격 없음)
python scripts/create_multiple_accounts.py --env qa --count 5 --delay 0 --fast

# 오류시에도 계속 진행
python scripts/create_multiple_accounts.py --env qa --count 10 --continue-on-error
```

## ⚙️ 주요 옵션

### 환경 설정
- `--env qa`: QA 테스트 환경 (@benx.com 도메인)
- `--env real`: 실제 운영 환경 (Gmail dot 방식)

### 이메일 설정
- `--base-email`: Real 환경에서 사용할 기본 Gmail 주소
- `--email`: QA 환경에서 직접 지정할 이메일

### 계정 설정
- `--password`: 사용자 지정 비밀번호 (없으면 자동 생성)
- `--nickname`: 사용자 지정 닉네임 (없으면 자동 생성)
- `--count`: 생성할 계정 수

### 실행 옵션
- `--delay`: 계정 생성 간격 (초)
- `--headless`: 브라우저 헤드리스 모드
- `--verbose`: 상세 출력 모드
- `--fast`: 확인 없이 바로 실행
- `--continue-on-error`: 오류 발생시에도 계속 진행

### 알림 설정
- `--slack-webhook`: Slack 웹훅 URL
- `--no-slack`: Slack 알림 비활성화

## 결과 파일

생성된 계정 정보는 `output/` 폴더에 JSON 형태로 저장됩니다:

```json
{
  "environment": "qa",
  "created_at": "2024-01-01T12:00:00",
  "total_accounts": 5,
  "successful_accounts": 4,
  "failed_accounts": 1,
  "accounts": [
    {
      "email": "test123@benx.com",
      "password": "AutoGen123!",
      "nickname": "Member_abc123",
      "wid": "WID123456789",
      "status": "completed",
      "created_at": "2024-01-01 12:00:00",
      "updated_at": "2024-01-01 12:02:30",
      "environment": "qa"
    }
  ]
}
```


## 문제 발생 케이스

### 일반적인 오류

1. **Playwright 브라우저 없음**
   ```bash
   playwright install chromium
   ```

2. **Gmail API 인증 실패**
   - `credentials.json` 파일 확인
   - Google Cloud Console에서 API 활성화 확인

3. **계정 생성 실패**
   - 네트워크 연결 확인
   - 위버스 사이트 상태 확인
   - 브라우저 헤드리스 모드 해제해서 디버깅

