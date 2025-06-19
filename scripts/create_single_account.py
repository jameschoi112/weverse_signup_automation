#!/usr/bin/env python3
"""
단일 위버스 계정 생성 스크립트
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
from utils.helpers import print_account_details


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='단일 위버스 계정 생성기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # QA 환경에서 랜덤 계정 생성
  python scripts/create_single_account.py --env qa

  # Real 환경에서 Gmail 기반 계정 생성
  python scripts/create_single_account.py --env real --base-email test@gmail.com

  # 사용자 지정 비밀번호와 닉네임으로 계정 생성
  python scripts/create_single_account.py --env qa --password mypass123 --nickname TestUser

  # 특정 이메일로 계정 생성 (QA 환경에서만)
  python scripts/create_single_account.py --env qa --email custom@benx.com
        """
    )

    parser.add_argument('--env', choices=['qa', 'real'], required=True,
                        help='환경 설정 (qa: 테스트, real: 실제)')
    parser.add_argument('--base-email', help='기본 Gmail 주소 (real 환경시 필요)')
    parser.add_argument('--email', help='직접 지정할 이메일 (qa 환경에서만 사용)')
    parser.add_argument('--password', help='사용자 지정 비밀번호')
    parser.add_argument('--nickname', help='사용자 지정 닉네임')
    parser.add_argument('--slack-webhook', help='Slack 웹훅 URL')
    parser.add_argument('--no-slack', action='store_true', help='Slack 알림 비활성화')
    parser.add_argument('--verbose', action='store_true', help='상세 출력 모드')
    parser.add_argument('--save-file', help='결과 저장 파일명')
    parser.add_argument('--headless', action='store_true', help='브라우저 헤드리스 모드')

    return parser.parse_args()


def validate_args(args):
    """인수 유효성 검사"""
    errors = []

    if args.env == 'real' and not args.base_email:
        errors.append("Real 환경에서는 --base-email이 필요합니다.")

    if args.email and args.env == 'real':
        errors.append("--email 옵션은 QA 환경에서만 사용할 수 있습니다.")

    if args.base_email and args.email:
        errors.append("--base-email과 --email은 동시에 사용할 수 없습니다.")

    return errors


class SingleAccountCreator(WeverseAccountCreator):
    """단일 계정 생성을 위한 확장 클래스"""

    def __init__(self, config: AccountCreationConfig, specific_email: str = None):
        super().__init__(config)
        self.specific_email = specific_email

    async def create_single_account_with_email(self, browser, email: str = None):
        """특정 이메일로 단일 계정 생성"""
        if email:
            # 이메일이 지정된 경우 이메일 생성기를 우회
            original_generate = self.email_generator.generate_email
            self.email_generator.generate_email = lambda env, base: email

            try:
                account = await self.create_single_account(browser, 0)
                return account
            finally:
                # 원래 메서드 복원
                self.email_generator.generate_email = original_generate
        else:
            return await self.create_single_account(browser, 0)


async def main():
    """메인 함수"""
    args = parse_arguments()

    print("🎯 단일 위버스 계정 생성기 v1.0")
    print("=" * 50)

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

    if args.email:
        print(f"이메일: {args.email} (직접 지정)")
    elif args.env == 'real':
        print(f"이메일 방식: Gmail dot 방식")
        print(f"기본 이메일: {args.base_email}")
    else:
        print(f"이메일 방식: @benx.com 랜덤 생성")

    if args.password:
        print(f"비밀번호: 사용자 지정")
    else:
        print(f"비밀번호: 자동 생성")

    if args.nickname:
        print(f"닉네임: {args.nickname}")
    else:
        print(f"닉네임: 자동 생성")

    print(f"Slack 알림: {'활성화' if slack_webhook_url else '비활성화'}")
    print(f"브라우저 모드: {'헤드리스' if args.headless else '일반'}")
    print()

    try:
        # 계정 생성 설정
        config_dict = {
            'environment': args.env,
            'count': 1,
            'base_email': args.base_email,
            'custom_password': args.password,
            'custom_nickname': args.nickname,
            'delay': 0,
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
        creator = SingleAccountCreator(config, args.email)



        # 서비스 초기화
        await creator.initialize_services()

        # 계정 생성 실행
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)

            try:
                account = await creator.create_single_account_with_email(browser, args.email)

                # 결과 출력
                print(f"\n{'=' * 50}")
                print("계정 생성 완료")
                print(f"{'=' * 50}")

                if args.verbose:
                    print_account_details([account])
                else:
                    print(f"이메일: {account.email}")
                    print(f"비밀번호: {account.password}")
                    print(f"닉네임: {account.nickname}")
                    print(f"WID: {account.wid or 'N/A'}")
                    print(f"상태: {account.status}")

                # 결과 파일 저장
                if args.save_file or account.is_completed():
                    saved_file = creator.save_results(args.save_file)
                    print(f"결과 파일: {saved_file}")

                # 성공 여부에 따른 종료 코드
                return 0 if account.is_completed() else 1

            finally:
                await browser.close()

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