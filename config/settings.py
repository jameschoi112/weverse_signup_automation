"""
위버스 자동화 설정 파일
"""
import os
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent

# 위버스 URL 설정
WEVERSE_URLS = {
    "signup": "https://account.weverse.io/ko/signup?client_id=weverse&redirect_uri=https%3A%2F%2Fweverse.io%2F&redirect_method=COOKIE",
    "login": "https://account.weverse.io/ko/login",
    "profile": "https://weverse.io/",
}

# 이메일 설정
EMAIL_SETTINGS = {
    "qa_domain": "@benx.com",
    "gmail_domain": "@gmail.com",
    "verification_timeout": 120,  # 인증 대기 시간(초)
}

# 계정 생성 설정
ACCOUNT_SETTINGS = {
    "password_length_min": 8,
    "password_length_max": 12,
    "nickname_prefix": "Member_",
    "nickname_suffix_length": 6,
    "default_delay": 5,  # 계정 생성 간격(초)
}

# Playwright 설정
BROWSER_SETTINGS = {
    "headless": False,
    "timeout": 30000,  # 기본 타임아웃(밀리초)
    "wait_timeout": 15000,  # 요소 대기 타임아웃(밀리초)
}

# Gmail API 설정 (절대 경로 사용)
GMAIL_SETTINGS = {
    "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
    "credentials_file": str(PROJECT_ROOT / "credentials.json"),  # 절대 경로
    "token_file": str(PROJECT_ROOT / "gmail_token.pickle"),      # 절대 경로
    "max_search_attempts": 30,
    "search_interval": 5,  # 검색 간격(초)
}

# Slack 설정
SLACK_SETTINGS = {
    "default_webhook_url": "https://hooks.slack.com/services/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",
    "timeout": 10,  # 요청 타임아웃(초)
}

# 로그 설정
LOG_SETTINGS = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": PROJECT_ROOT / "logs" / "weverse_automation.log",
    "max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}

# 출력 설정
OUTPUT_SETTINGS = {
    "directory": PROJECT_ROOT / "output",
    "filename_format": "weverse_accounts_{env}_{timestamp}.json",
    "timestamp_format": "%Y%m%d_%H%M%S",
}

# 환경별 설정
ENVIRONMENT_SETTINGS = {
    "qa": {
        "email_domain": EMAIL_SETTINGS["qa_domain"],
        "description": "QA 테스트 환경",
    },
    "real": {
        "email_domain": EMAIL_SETTINGS["gmail_domain"],
        "description": "실제 운영 환경",
        "require_base_email": True,
    },
}

# 개발 설정
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
VERBOSE = os.getenv("VERBOSE", "False").lower() == "true"