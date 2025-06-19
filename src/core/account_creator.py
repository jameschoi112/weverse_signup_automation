"""
메인 계정 생성기
"""
import asyncio
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from models.account import AccountInfo, AccountCreationConfig, AccountStatus
from services.email_generator import EmailGenerator
from services.gmail_service import GmailService
from services.slack_service import SlackService
from services.weverse_service import WeverseService
from utils.helpers import generate_password, generate_nickname, save_accounts_to_file, print_account_summary


class WeverseAccountCreator:
    """위버스 계정 생성기 메인 클래스"""

    def __init__(self, config: AccountCreationConfig):
        """
        계정 생성기 초기화

        Args:
            config: 계정 생성 설정
        """
        self.config = config
        self.accounts: List[AccountInfo] = []

        # 서비스 초기화
        self.email_generator = EmailGenerator()
        self.gmail_service = GmailService() if config.gmail_account else None
        self.slack_service = SlackService(config.slack_webhook_url) if config.slack_webhook_url else None
        self.weverse_service = WeverseService()

        print(f"[INIT] 계정 생성기 초기화 완료 ({config.environment.upper()} 환경)")

    async def initialize_services(self) -> bool:
        """외부 서비스들 초기화"""
        success = True

        # Gmail 서비스 초기화
        if self.gmail_service:
            gmail_init = await self.gmail_service.initialize()
            if not gmail_init:
                print("[WARNING] Gmail 서비스 초기화 실패 - 수동 인증으로 진행")
                self.gmail_service = None
            else:
                print("[INFO] Gmail 서비스 초기화 완료")

        return success

    async def create_single_account(self, browser: Browser, index: int = 0) -> AccountInfo:
        """단일 계정 생성"""
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 계정 정보 생성
            email = self.email_generator.generate_email(
                self.config.environment,
                self.config.base_email
            )
            password = generate_password(self.config.custom_password)
            nickname = generate_nickname(
                self.config.custom_nickname,
                index if self.config.count > 1 else None
            )

            account_info = AccountInfo(
                email=email,
                password=password,
                nickname=nickname,
                environment=self.config.environment
            )

            print(f"\n{'=' * 50}")
            print(f"[START] 계정 생성 시작: {email}")
            print(f"[INFO] 환경: {self.config.environment.upper()}")
            print(f"[INFO] 비밀번호: {'사용자 지정' if self.config.custom_password else '자동 생성'}")
            print(f"[INFO] 닉네임: {'사용자 지정' if self.config.custom_nickname else '자동 생성'}")
            print(f"{'=' * 50}")

            # 1. 회원가입 폼 작성
            signup_success = await self.weverse_service.fill_signup_form(page, account_info)
            if not signup_success:
                if self.slack_service:
                    await self.slack_service.send_error_notification(
                        f"회원가입 폼 작성 실패: {account_info.status}",
                        account_info
                    )
                return account_info

            # 2. 이메일 인증 처리
            await self._handle_email_verification(account_info)

            # 3. 로그인 및 WID 추출 (마이페이지 방식)
            if account_info.status == AccountStatus.EMAIL_VERIFIED.value:
                is_multi_account = self.config.count > 1
                await self._login_and_extract_wid(page, account_info, is_multi_account)

            # 4. 최종 결과 알림
            await self._send_final_notification(account_info)

            self.accounts.append(account_info)
            print(f"[COMPLETE] 계정 처리 완료: {email} (상태: {account_info.status})")

            return account_info

        except Exception as e:
            print(f"[ERROR] 계정 생성 중 오류: {e}")
            if 'account_info' in locals():
                account_info.update_status(AccountStatus.CREATION_FAILED)
                if self.slack_service:
                    await self.slack_service.send_error_notification(str(e), account_info)
                return account_info
            else:
                # account_info가 생성되지 않은 경우
                error_account = AccountInfo(
                    email="unknown",
                    password="unknown",
                    nickname="unknown",
                    environment=self.config.environment
                )
                error_account.update_status(AccountStatus.CREATION_FAILED)
                return error_account

        finally:
            await context.close()

    async def create_multiple_accounts(self) -> List[AccountInfo]:
        """다중 계정 생성"""
        print(f"\n계정 생성 시작 (총 {self.config.count}개) / ({self.config.environment.upper()} 환경)")

        # 서비스 초기화
        await self.initialize_services()

        start_time = datetime.now()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)

            try:
                for i in range(self.config.count):
                    print(f"\n[{i + 1}/{self.config.count}] 계정 생성 중...")

                    account_info = await self.create_single_account(browser, i + 1)

                    # 다음 계정 생성 전 대기
                    if i < self.config.count - 1 and self.config.delay > 0:
                        print(f"[WAIT] {self.config.delay}초 대기 중...")
                        await asyncio.sleep(self.config.delay)

            finally:
                await browser.close()

        end_time = datetime.now()

        # 최종 요약
        await self._send_summary_notification(start_time, end_time)

        return self.accounts

    async def _handle_email_verification(self, account_info: AccountInfo):
        """이메일 인증 처리"""
        try:
            print(f"[STEP 5] 이메일 인증 처리 시작")

            # 약관 동의 후 잠시 대기
            await asyncio.sleep(3)

            if self.slack_service:
                await self.slack_service.send_notification(
                    "[계정 생성 완료] 이메일 인증 처리 대기",
                    account_info
                )

            # Gmail 인증 처리
            if self.gmail_service:
                verification_success = await self._process_gmail_verification(account_info.email)

                if verification_success:
                    account_info.update_status(AccountStatus.EMAIL_VERIFIED)
                    print(f"[SUCCESS] 이메일 인증 완료: {account_info.email}")

                    if self.slack_service:
                        await self.slack_service.send_notification(
                            "[이메일 인증 완료] 로그인 및 WID 추출 중...",
                            account_info
                        )
                else:
                    account_info.update_status(AccountStatus.EMAIL_VERIFICATION_FAILED)
                    print(f"[ERROR] 이메일 인증 실패: {account_info.email}")
            else:
                # Gmail 서비스가 없는 경우 수동 처리
                print("[INFO] Gmail 서비스가 없어 수동 인증으로 전환")
                account_info.update_status(AccountStatus.EMAIL_VERIFICATION_PENDING)

        except Exception as e:
            print(f"[ERROR] 이메일 인증 처리 실패: {e}")
            account_info.update_status(AccountStatus.EMAIL_VERIFICATION_FAILED)

    async def _process_gmail_verification(self, target_email: str) -> bool:
        """Gmail을 통한 인증 처리"""
        if not self.gmail_service:
            return False

        try:
            print(f"[GMAIL] Gmail을 통해 인증 메일 확인 중...")

            # 인증 메일에서 링크 찾기
            verification_link = await self.gmail_service.find_verification_email(target_email)

            if verification_link:
                print(f"[GMAIL] 인증 링크 발견: {verification_link}")

                # Slack으로 인증 링크 전송
                if self.slack_service:
                    await self.slack_service.send_verification_link(verification_link, target_email)

                    # 사용자가 클릭할 시간 대기
                    print("[SLACK] 슬랙에서 인증 링크를 클릭해주세요. 남은시간: 1분 30초")
                    await asyncio.sleep(90)

                    print("[INFO] 인증 대기 시간 완료. 다음 단계 진행.")
                    return True
                else:
                    print(f"[MANUAL] 수동으로 다음 링크를 클릭해주세요: {verification_link}")
                    return True
            else:
                print("[GMAIL] 인증 메일을 찾을 수 없습니다.")
                return False

        except Exception as e:
            print(f"[ERROR] Gmail 인증 처리 중 오류: {e}")
            return False

    async def _login_and_extract_wid(self, page: Page, account_info: AccountInfo, is_multi_account: bool):
        """로그인 및 WID 추출 (마이페이지 방식)"""
        try:
            print(f"[STEP 6] 로그인 및 WID 추출 시작")

            # 일반 로그인 시도
            login_success = await self.weverse_service.login_and_extract_wid(page, account_info, is_multi_account)

            if login_success:
                print(f"[SUCCESS] 로그인 및 WID 추출 완료: {account_info.wid}")
                return

            # 일반 로그인 실패시 추가 인증 필요한지 확인
            print("[INFO] 일반 로그인 실패 - 추가 인증 필요 여부 확인 중...")

            # 페이지 상태 확인 - 추가 인증 필요한지 체크
            try:
                await asyncio.sleep(2)  # 페이지 로딩 대기

                # 비정상적인 접근 메시지 확인
                abnormal_access_message = await page.query_selector('li:has-text("비정상적인 접근으로 감지되어, 인증이 필요합니다.")')
                if abnormal_access_message:
                    print("[INFO] 추가 인증이 필요함 - Gmail에서 인증 코드 확인 중...")

                    # Gmail 서비스가 있으면 추가 인증 처리
                    if self.gmail_service:
                        additional_auth_success = await self.weverse_service.handle_additional_verification_and_extract_wid(
                            page, account_info, self.gmail_service, is_multi_account
                        )

                        if additional_auth_success:
                            print(f"[SUCCESS] 추가 인증 후 WID 추출 완료: {account_info.wid}")
                        else:
                            print("[ERROR] 추가 인증 처리 실패")
                            account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)
                    else:
                        print("[WARNING] Gmail 서비스가 없어 추가 인증 처리 불가")
                        account_info.update_status(AccountStatus.EMAIL_VERIFICATION_FAILED)
                else:
                    print("[INFO] 추가 인증이 필요하지 않음 - 다른 오류로 인한 로그인 실패")
                    account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)

            except Exception as check_error:
                print(f"[ERROR] 추가 인증 확인 중 오류: {check_error}")
                account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)

        except Exception as e:
            print(f"[ERROR] 로그인 및 WID 추출 실패: {e}")
            account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)

    async def _send_final_notification(self, account_info: AccountInfo):
        """최종 결과 알림"""
        # 터미널에 간단한 결과 출력
        print(f"\n{'='*60}")
        print("계정 생성 최종 결과")

        print(f"ID(이메일): {account_info.email}")
        print(f"PW: {account_info.password}")
        print(f"WID: {account_info.wid or 'N/A'}")
        print(f"환경: {account_info.environment.upper()}")
        print(f"{'='*60}\n")

        if not self.slack_service:
            return

        try:
            if account_info.is_completed():
                await self.slack_service.send_success_notification(account_info)
            elif account_info.is_failed():
                await self.slack_service.send_error_notification(
                    f"계정 생성 실패 (상태: {account_info.status})",
                    account_info
                )
            else:
                await self.slack_service.send_notification(
                    f"계정 생성 미완료 (상태: {account_info.status})",
                    account_info
                )

        except Exception as e:
            print(f"[WARNING] 최종 알림 발송 실패: {e}")

    async def _send_summary_notification(self, start_time: datetime, end_time: datetime):
        """요약 알림 발송"""
        try:
            # 통계 계산
            total_count = len(self.accounts)
            success_count = len([acc for acc in self.accounts if acc.is_completed()])
            failed_count = len([acc for acc in self.accounts if acc.is_failed()])

            # 소요 시간 계산
            duration = end_time - start_time
            duration_str = f"{int(duration.total_seconds() // 60)}분 {int(duration.total_seconds() % 60)}초"

            print(f"\n{'=' * 60}")
            print(f"전체 작업 완료!")
            print(f"소요 시간: {duration_str}")
            print(f"총 {total_count}개 계정 (성공: {success_count}, 실패: {failed_count})")
            print(f"{'=' * 60}")

            # Slack 요약 알림
            if self.slack_service:
                await self.slack_service.send_bulk_summary(
                    total_count, success_count, failed_count, self.config.environment
                )

            # 결과 요약 출력
            print_account_summary(self.accounts, self.config.environment)

        except Exception as e:
            print(f"[WARNING] 요약 알림 발송 실패: {e}")

    def save_results(self, filename: str = None) -> str:
        """결과를 파일로 저장"""
        return save_accounts_to_file(self.accounts, self.config.environment, filename)

    def get_successful_accounts(self) -> List[AccountInfo]:
        """성공한 계정들만 반환"""
        return [acc for acc in self.accounts if acc.is_completed()]

    def get_failed_accounts(self) -> List[AccountInfo]:
        """실패한 계정들만 반환"""
        return [acc for acc in self.accounts if acc.is_failed()]

    def get_statistics(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        total = len(self.accounts)
        success = len(self.get_successful_accounts())
        failed = len(self.get_failed_accounts())
        pending = total - success - failed

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "pending": pending,
            "success_rate": (success / total * 100) if total > 0 else 0,
            "environment": self.config.environment,
        }

    def clear_accounts(self):
        """계정 목록 초기화"""
        self.accounts.clear()
        self.email_generator.clear_used_emails()

    def add_existing_account(self, account_info: AccountInfo):
        """기존 계정 정보 추가"""
        self.accounts.append(account_info)