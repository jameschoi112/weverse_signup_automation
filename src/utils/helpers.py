"""
공통 유틸리티 함수들
"""
import json
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from config.settings import ACCOUNT_SETTINGS, OUTPUT_SETTINGS
from models.account import AccountInfo


def generate_random_string(length: int = 8) -> str:
    """랜덤 문자열 생성"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def generate_password(custom_password: str = None) -> str:
    """비밀번호 생성 또는 사용자 지정 비밀번호 사용"""
    if custom_password:
        return custom_password

    # 랜덤 비밀번호 생성 (8-12자, 영문+숫자+특수문자)
    password = []

    # 각 조건을 만족하는 문자를 최소 1개씩 포함
    password.append(random.choice(string.ascii_uppercase))  # 대문자 1개
    password.append(random.choice(string.ascii_lowercase))  # 소문자 1개
    password.append(random.choice(string.digits))  # 숫자 1개
    password.append(random.choice("!@#$%^&*"))  # 특수문자 1개

    # 나머지 길이를 랜덤하게 채움
    min_length = ACCOUNT_SETTINGS["password_length_min"]
    max_length = ACCOUNT_SETTINGS["password_length_max"]
    remaining_length = random.randint(
        min_length - 4,
        max_length - 4
    )

    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password.extend(random.choices(all_chars, k=remaining_length))

    # 순서 섞기
    random.shuffle(password)
    return ''.join(password)


def generate_nickname(custom_nickname: str = None, index: int = None) -> str:
    """닉네임 생성 또는 사용자 지정 닉네임 사용"""
    if custom_nickname:
        if index is not None and index > 0:
            return f"{custom_nickname}_{index:02d}"
        return custom_nickname

    prefix = ACCOUNT_SETTINGS["nickname_prefix"]
    suffix_length = ACCOUNT_SETTINGS["nickname_suffix_length"]
    suffix = generate_random_string(suffix_length)
    return f"{prefix}{suffix}"


def save_accounts_to_file(accounts: List[AccountInfo], environment: str,
                          filename: str = None) -> str:
    """계정 정보를 파일로 저장"""
    if not filename:
        timestamp = datetime.now().strftime(OUTPUT_SETTINGS["timestamp_format"])
        filename = OUTPUT_SETTINGS["filename_format"].format(
            env=environment,
            timestamp=timestamp
        )

    # 출력 디렉토리 생성
    output_dir = OUTPUT_SETTINGS["directory"]
    output_dir.mkdir(exist_ok=True)

    filepath = output_dir / filename

    # 데이터 구성
    data = {
        "environment": environment,
        "created_at": datetime.now().isoformat(),
        "total_accounts": len(accounts),
        "successful_accounts": len([acc for acc in accounts if acc.is_completed()]),
        "failed_accounts": len([acc for acc in accounts if acc.is_failed()]),
        "accounts": [acc.to_dict() for acc in accounts]
    }

    # 파일 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n결과가 저장되었습니다: {filepath}")
    return str(filepath)


def load_accounts_from_file(filepath: str) -> List[AccountInfo]:
    """파일에서 계정 정보 로드"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        accounts = []
        for account_data in data.get('accounts', []):
            accounts.append(AccountInfo.from_dict(account_data))

        return accounts

    except Exception as e:
        print(f"[ERROR] 파일 로드 실패: {e}")
        return []


def print_account_summary(accounts: List[AccountInfo], environment: str):
    """계정 생성 결과 요약 출력"""
    total_count = len(accounts)
    success_count = len([acc for acc in accounts if acc.is_completed()])
    failed_count = len([acc for acc in accounts if acc.is_failed()])
    pending_count = total_count - success_count - failed_count

    print(f"\n{'=' * 60}")
    print(f"계정 생성 결과 ({environment.upper()} 환경)")
    print(f"{'=' * 60}")
    print(f"총 계정 수: {total_count}개")
    print(f"성공: {success_count}개")
    print(f"실패: {failed_count}개")
    print(f"대기 중: {pending_count}개")

    if total_count > 0:
        success_rate = (success_count / total_count) * 100
        print(f"성공률: {success_rate:.1f}%")

    print(f"{'=' * 60}")


def print_account_details(accounts: List[AccountInfo]):
    """계정 상세 정보 출력"""
    for i, account in enumerate(accounts, 1):
        print(f"\n[{i}] 계정 정보:")
        print(f"  ID (이메일): {account.email}")
        print(f"  PW (비밀번호): {account.password}")
        print(f"  닉네임: {account.nickname}")
        print(f"  WID: {account.wid or 'N/A'}")
        print(f"  상태: {account.status}")
        print(f"  생성시간: {account.created_at}")
        if account.updated_at != account.created_at:
            print(f"  수정시간: {account.updated_at}")


def format_duration(start_time: datetime, end_time: datetime = None) -> str:
    """소요 시간 포맷팅"""
    if end_time is None:
        end_time = datetime.now()

    duration = end_time - start_time
    total_seconds = int(duration.total_seconds())

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}시간 {minutes}분 {seconds}초"
    elif minutes > 0:
        return f"{minutes}분 {seconds}초"
    else:
        return f"{seconds}초"


def get_status_emoji(status: str) -> str:
    """상태에 따른 이모지 반환"""
    status_emojis = {
        "created": "🆕",
        "email_step_failed": "❌",
        "password_step_failed": "❌",
        "nickname_step_failed": "❌",
        "terms_step_failed": "❌",
        "email_verification_pending": "⏳",
        "email_verification_failed": "❌",
        "email_verified": "✅",
        "wid_extraction_failed": "⚠️",
        "completed": "🎉",
        "creation_failed": "❌",
    }
    return status_emojis.get(status, "❓")


def create_progress_bar(current: int, total: int, width: int = 50) -> str:
    """진행률 바 생성"""
    if total == 0:
        return "[" + "=" * width + "]"

    progress = current / total
    filled_width = int(width * progress)

    bar = "=" * filled_width + "-" * (width - filled_width)
    percentage = progress * 100

    return f"[{bar}] {percentage:.1f}% ({current}/{total})"


def sanitize_filename(filename: str) -> str:
    """파일명에서 특수문자 제거"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def ensure_directory_exists(directory: Path) -> bool:
    """디렉토리 존재 확인 및 생성"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"[ERROR] 디렉토리 생성 실패: {e}")
        return False


def validate_email_format(email: str) -> bool:
    """이메일 형식 검증"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
    """민감한 데이터 마스킹 (비밀번호 등)"""
    if len(text) <= 2:
        return mask_char * len(text)
    return text[0] + mask_char * (len(text) - 2) + text[-1]


def get_account_statistics(accounts: List[AccountInfo]) -> Dict[str, Any]:
    """계정 통계 정보 생성"""
    stats = {
        "total": len(accounts),
        "completed": 0,
        "failed": 0,
        "pending": 0,
        "by_status": {},
        "environments": {},
        "creation_times": [],
    }

    for account in accounts:
        # 상태별 카운트
        if account.is_completed():
            stats["completed"] += 1
        elif account.is_failed():
            stats["failed"] += 1
        else:
            stats["pending"] += 1

        # 세부 상태별 카운트
        status = account.status
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

        # 환경별 카운트
        env = account.environment
        stats["environments"][env] = stats["environments"].get(env, 0) + 1

        # 생성 시간 수집
        if account.created_at:
            stats["creation_times"].append(account.created_at)

    # 성공률 계산
    if stats["total"] > 0:
        stats["success_rate"] = (stats["completed"] / stats["total"]) * 100
    else:
        stats["success_rate"] = 0

    return stats