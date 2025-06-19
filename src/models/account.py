"""
계정 정보 모델
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AccountStatus(Enum):
    """계정 상태 열거형"""
    CREATED = "created"
    EMAIL_STEP_FAILED = "email_step_failed"
    PASSWORD_STEP_FAILED = "password_step_failed"
    NICKNAME_STEP_FAILED = "nickname_step_failed"
    TERMS_STEP_FAILED = "terms_step_failed"
    EMAIL_VERIFICATION_PENDING = "email_verification_pending"
    EMAIL_VERIFICATION_FAILED = "email_verification_failed"
    EMAIL_VERIFIED = "email_verified"
    WID_EXTRACTION_FAILED = "wid_extraction_failed"
    COMPLETED = "completed"
    CREATION_FAILED = "creation_failed"


@dataclass
class AccountInfo:
    """계정 정보를 저장하는 데이터 클래스"""
    email: str
    password: str
    nickname: str
    wid: Optional[str] = None
    status: str = AccountStatus.CREATED.value
    created_at: str = ""
    updated_at: str = ""
    environment: str = "qa"

    def __post_init__(self):
        """초기화 후 처리"""
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def update_status(self, status: AccountStatus) -> None:
        """상태 업데이트"""
        self.status = status.value
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def set_wid(self, wid: str) -> None:
        """WID 설정"""
        self.wid = wid
        self.status = AccountStatus.COMPLETED.value
        self.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def is_completed(self) -> bool:
        """계정 생성 완료 여부"""
        return self.status == AccountStatus.COMPLETED.value

    def is_failed(self) -> bool:
        """계정 생성 실패 여부"""
        failed_statuses = [
            AccountStatus.EMAIL_STEP_FAILED.value,
            AccountStatus.PASSWORD_STEP_FAILED.value,
            AccountStatus.NICKNAME_STEP_FAILED.value,
            AccountStatus.TERMS_STEP_FAILED.value,
            AccountStatus.EMAIL_VERIFICATION_FAILED.value,
            AccountStatus.WID_EXTRACTION_FAILED.value,
            AccountStatus.CREATION_FAILED.value,
        ]
        return self.status in failed_statuses

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountInfo':
        """딕셔너리에서 객체 생성"""
        return cls(**data)

    def __str__(self) -> str:
        """문자열 표현"""
        return f"AccountInfo(email={self.email}, status={self.status}, wid={self.wid})"

    def __repr__(self) -> str:
        """개발자용 문자열 표현"""
        return (f"AccountInfo(email='{self.email}', password='***', "
                f"nickname='{self.nickname}', wid='{self.wid}', "
                f"status='{self.status}')")


@dataclass
class AccountCreationConfig:
    """계정 생성 설정"""
    environment: str = "qa"
    count: int = 1
    base_email: Optional[str] = None
    custom_password: Optional[str] = None
    custom_nickname: Optional[str] = None
    delay: int = 5
    slack_webhook_url: Optional[str] = None
    gmail_account: Optional[Dict[str, str]] = None

    def __post_init__(self):
        """초기화 후 검증"""
        if self.environment == "real" and not self.base_email:
            raise ValueError("Real 환경에서는 base_email이 필요합니다")

        if self.count <= 0:
            raise ValueError("count는 1 이상이어야 합니다")

        if self.delay < 0:
            raise ValueError("delay는 0 이상이어야 합니다")

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)