#!/usr/bin/env python3
"""
다중 위버스 계정 생성 스크립트
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from models.account import AccountCreationConfig
from core.account_creator import WeverseAccountCreator
from utils.helpers import print_account_details, create_progress_bar


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='다중 위버스 계정 생성기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # QA 환경에서 5개 계정 생성
  python scripts/create_multiple_accounts.py --env qa --count 5

  # Real 환경에서 Gmail 기반 10개 계정 생성 (3초 간격)
  python scripts/create_multiple_accounts.py --env real --count 10 --base-email test@gmail.com --delay 3

  # 사용자 지정 설정으로 계정 생성
  python scripts/create_multiple_accounts.py --env qa --count 3 --password mypass123 --nickname TestUser

  # 빠른 생성 (간격 없음)
  python scripts/create_multiple_accounts.py --env qa --count 5 --delay 0 --fast
        """
    )

    parser.add_argument('--env', choices=['qa', 'real'], required=True,
                        help='환경 설정 (qa: 테스트, real: 실제)')
    parser.add_argument('--count', type=int, required=True,
                        help='생성할 계정 수')
    parser.add_argument('--base-email', help='기본 Gmail 주소 (real 환경시 필요)')
    parser.add_argument('--password', help='사용자 지정 비밀번호')
    parser.add_argument('--nickname', help='사용자 지정 닉네임 (순번이 자동 추가됨)')
    parser.add_argument('--delay', type=int, default=5,
                        help='계정 생성 간격 (초, 기본값: 5)')
    parser.add_argument('--slack-webhook', help='Slack 웹훅 URL')
    parser.add_argument('--no-slack', action='store_true', help='Slack 알림 비활성화')
    parser.add_argument('--verbose', action='store_true', help='상세 출력 모드')
    parser.add_argument('--save-file', help='결과 저장 파일명')
    parser.add_argument('--headless', action='store_true', help='브라우저 헤드리스 모드')
    parser.add_argument('--fast', action='store_true', help='빠른 생성 모드 (확인 없이 바로 실행)')
    parser.add_argument('--continue-on-error', action='store_true',
                        help='오류 발생시에도 계속 진행')
    parser.add_argument('--max-concurrent', type=int, default=1,
                        help='동시 실행할 브라우저 수 (기본값: 1, 실험적 기능)')

    return parser.parse_args()


def validate_args(args):
    """인수 유효성 검사"""
    errors = []

    if args.env == 'real' and not args.base_email:
        errors.append("Real 환경에서는 --base-email이 필요합니다.")

    if args.count <= 0:
        errors.append("계정 수는 1 이상이어야 합니다.")

    if args.count > 100:
        errors.append("계정 수는 100개 이하로 제한됩니다.")

    if args.delay < 0:
        errors.append("생성 간격은 0 이상이어야 합니다.")

    if args.max_concurrent <= 0:
        errors.append("동시 실행 수는 1 이상이어야 합니다.")

    if args.max_concurrent > 5:
        errors.append("동시 실행 수는 5개 이하로 제한됩니다.")

    return errors


class MultiAccountCreator(WeverseAccountCreator):
    """다중 계정 생성을 위한 확장 클래스"""

    def __init__(self, config: AccountCreationConfig, continue_on_error: bool = False):
        super().__init__(config)
        self.continue_on_error = continue_on_error
        self.progress_callback = None

    def set_progress_callback(self, callback):
        """진행률 콜백 설정"""
        self.progress_callback = callback

    async def create_multiple_accounts_with_progress(self):
        """진행률 표시와 함께 다중 계정 생성"""
        print(f"\n계정 생성 시작 (총 {self.config.count}개) / ({self.config.environment.upper()} 환경)")

        # 서비스 초기화
        await self.initialize_services()

        from datetime import datetime
        start_time = datetime.now()

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # 설정에 따라 변경 가능

            try:
                for i in range(self.config.count):
                    current = i + 1

                    # 진행률 표시
                    progress_bar = create_progress_bar(i, self.config.count)
                    print(f"\n{progress_bar}")
                    print(f"[{current}/{self.config.count}] 계정 생성 중...")

                    try:
                        account_info = await self.create_single_account(browser, current)

                        # 진행률 콜백 호출
                        if self.progress_callback:
                            self.progress_callback(current, self.config.count, account_info)

                        # 결과 요약 출력
                        status_emoji = "🎉" if account_info.is_completed() else "❌" if account_info.is_failed() else "⏳"
                        print(f"{status_emoji} {account_info.email} - {account_info.status}")

                    except Exception as e:
                        print(f"❌ 계정 생성 실패: {e}")

                        if not self.continue_on_error:
                            print("오류로 인해 중단됩니다. --continue-on-error 옵션을 사용하면 계속 진행할 수 있습니다.")
                            break
                        else:
                            print("오류가 발생했지만 계속 진행합니다.")

                    # 다음 계정 생성 전 대기
                    if current < self.config.count and self.config.delay > 0:
                        print(f"⏱️ {self.config.delay}초 대기 중...")
                        await asyncio.sleep(self.config.delay)

            finally:
                await browser.close()

        end_time = datetime.now()

        # 최종 진행률 표시
        final_progress = create_progress_bar(self.config.count, self.config.count)
        print(f"\n{final_progress}")
        print("✅ 모든 계정 생성 작업 완료!")

        # 최종 요약
        await self._send_summary_notification(start_time, end_time)

        return self.accounts


def print_live_statistics(accounts, current, total):
    """실시간 통계 출력"""
    if not accounts:
        return

    success = len([acc for acc in accounts if acc.is_completed()])
    failed = len([acc for acc in accounts if acc.is_failed()])
    pending = len(accounts) - success - failed

    print(f"\n📊 현재 통계 ({current}/{total}):")
    print(f"  성공: {success}개")
    print(f"  실패: {failed}개")
    print(f"  대기: {pending}개")
    if current > 0:
        success_rate = (success / current) * 100
        print(f"  성공률: {success_rate:.1f}%")


async def main():
    """메인 함수"""
    args = parse_arguments()

    print("🚀 다중 위버스 계정 생성기 v1.0")
    print("=" * 60)

    # 인수 유효성 검사
    validation_errors = validate_args(args)
    if validation_errors:
        print("❌ 설정 오류:")
        for error in validation_errors:
            print(f"  - {error}")
        return 1

    # Slack 웹훅 설정
    slack_webhook_url = None
    if not args.no_slack:
        slack_webhook_url = args.slack_webhook or "https://hooks.slack.com/services/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"

    # 설정 표시
    print(f"📋 계정 생성 설정:")
    print(f"환경: {args.env.upper()}")
    print(f"계정 수: {args.count}개")

    if args.env == 'real':
        print(f"이메일 방식: Gmail dot 방식")
        print(f"기본 이메일: {args.base_email}")
    else:
        print(f"이메일 방식: @benx.com 랜덤 생성")

    if args.password:
        print(f"비밀번호: 사용자 지정")
    else:
        print(f"비밀번호: 자동 생성")

    if args.nickname:
        print(f"닉네임: {args.nickname}_XX (순번 자동 추가)")
    else:
        print(f"닉네임: 자동 생성")

    print(f"생성 간격: {args.delay}초")
    print(f"Slack 알림: {'활성화' if slack_webhook_url else '비활성화'}")
    print(f"브라우저 모드: {'헤드리스' if args.headless else '일반'}")
    print(f"오류 처리: {'계속 진행' if args.continue_on_error else '중단'}")

    # 예상 소요 시간 계산
    estimated_time = args.count * (30 + args.delay)  # 계정당 약 30초 + 대기시간
    estimated_minutes = estimated_time // 60
    print(f"예상 소요 시간: 약 {estimated_minutes}분")

    # 확인 (fast 모드가 아닌 경우)
    if not args.fast:
        print()
        confirm = input("계속 진행하시겠습니까? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("취소되었습니다.")
            return 0

    try:
        # 계정 생성 설정
        config_dict = {
            'environment': args.env,
            'count': args.count,
            'base_email': args.base_email,
            'custom_password': args.password,
            'custom_nickname': args.nickname,
            'delay': args.delay,
            'slack_webhook_url': slack_webhook_url,
            'gmail_account': {
                "email": "weversetestmail@gmail.com",
                "password": "not_needed_for_api"
            }
        }

        config = AccountCreationConfig(**config_dict)

        # 브라우저 설정 적용
        if args.headless:
            from config.settings import BROWSER_SETTINGS
            BROWSER_SETTINGS["headless"] = True

        # 계정 생성기 초기화
        creator = MultiAccountCreator(config, args.continue_on_error)

        # 진행률 콜백 설정
        def progress_callback(current, total, account):
            if args.verbose:
                print_live_statistics(creator.accounts, current, total)

        creator.set_progress_callback(progress_callback)

        print(f"\n🎯 계정 생성을 시작합니다...")

        # 계정 생성 실행
        accounts = await creator.create_multiple_accounts_with_progress()

        # 결과 출력
        if args.verbose:
            print_account_details(accounts)

        # 결과 파일 저장
        saved_file = creator.save_results(args.save_file)

        # 통계 정보
        stats = creator.get_statistics()
        print(f"\n📊 최종 통계:")
        print(f"총 계정: {stats['total']}개")
        print(f"성공: {stats['success']}개")
        print(f"실패: {stats['failed']}개")
        print(f"대기: {stats['pending']}개")
        print(f"성공률: {stats['success_rate']:.1f}%")
        print(f"결과 파일: {saved_file}")

        # 성공한 계정이 있으면 성공 코드
        return 0 if stats['success'] > 0 else 1

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        return 130

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
        sys.exit(130)