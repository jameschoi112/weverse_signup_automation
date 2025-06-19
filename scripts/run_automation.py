#!/usr/bin/env python3
"""
위버스 계정 자동 생성 메인 실행 스크립트
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 환경 변수로도 경로 추가 (PyCharm 호환성)
os.environ['PYTHONPATH'] = str(src_path) + os.pathsep + os.environ.get('PYTHONPATH', '')

try:
    from models.account import AccountCreationConfig
    from core.account_creator import WeverseAccountCreator
    from utils.helpers import print_account_details
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print(f"현재 Python 경로: {sys.path}")
    print(f"src 경로: {src_path}")
    sys.exit(1)


def get_user_input():
    """사용자로부터 대화형 입력받기"""

    # 환경 선택
    while True:
        env = input("\n환경을 직접 입력해주세요. (qa/real): ").strip().lower()
        if env in ['qa', 'real']:
            break
        print("'qa' 또는 'real'만 입력해주세요.")

    # 계정 수 입력
    while True:
        try:
            count = int(input("생성할 계정 수를 입력하세요: ").strip())
            if count > 0:
                break
            else:
                print("1 이상의 숫자를 입력해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")

    # Real 환경일 경우 기본 이메일 입력
    base_email = None
    if env == "real":
        print("\n📧 Real 환경에서는 Gmail dot 방식을 사용합니다.")
        base_email = input("기본 Gmail 주소를 입력하세요 (예: test@gmail.com): ").strip()
        if not base_email or '@gmail.com' not in base_email.lower():
            print("⚠️ Gmail 주소를 정확히 입력해주세요.")
            base_email = input("기본 Gmail 주소를 입력하세요 (예: test@gmail.com): ").strip()

    # 사용자 지정 설정
    custom_password = None
    custom_nickname = None

    use_custom = input("\n사용자 지정 설정을 사용하시겠습니까? (y/n): ").strip().lower()
    if use_custom in ['y', 'yes']:
        custom_password = input("비밀번호를 지정하세요 (엔터=자동생성): ").strip()
        if not custom_password:
            custom_password = None

        custom_nickname = input("닉네임을 지정하세요 (엔터=자동생성): ").strip()
        if not custom_nickname:
            custom_nickname = None
        elif count > 1:
            print(f"💡 여러 계정 생성시 닉네임에 _01, _02 등이 자동 추가됩니다.")

    # 생성 간격 설정
    while True:
        try:
            delay = int(input("\n계정 생성 간격을 설정하세요 (초, 기본값: 5): ").strip() or "5")
            if delay >= 0:
                break
            else:
                print("0 이상의 숫자를 입력해주세요.")
        except ValueError:
            print("숫자를 입력해주세요.")

    return {
        'environment': env,
        'count': count,
        'base_email': base_email,
        'custom_password': custom_password,
        'custom_nickname': custom_nickname,
        'delay': delay,
        # 슬랙 설정 고정
        'slack_webhook_url': "https://hooks.slack.com/services/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",
        'gmail_account': {
            "email": "weversetestmail@gmail.com",
            "password": "not_needed_for_api"
        }
    }


def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(
        description='위버스 계정 자동 생성기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 대화형 모드로 실행
  python scripts/run_automation.py --interactive

  # QA 환경에서 3개 계정 생성
  python scripts/run_automation.py --env qa --count 3

  # Real 환경에서 Gmail 기반 5개 계정 생성
  python scripts/run_automation.py --env real --count 5 --base-email test@gmail.com

  # 사용자 지정 비밀번호와 닉네임으로 계정 생성
  python scripts/run_automation.py --env qa --count 2 --password mypass123 --nickname TestUser
        """
    )

    parser.add_argument('--env', choices=['qa', 'real'], help='환경 설정 (qa: 테스트, real: 실제)')
    parser.add_argument('--count', type=int, help='생성할 계정 수')
    parser.add_argument('--base-email', help='기본 Gmail 주소 (real 환경시 필요)')
    parser.add_argument('--password', help='사용자 지정 비밀번호')
    parser.add_argument('--nickname', help='사용자 지정 닉네임')
    parser.add_argument('--delay', type=int, default=5, help='계정 생성 간격 (초, 기본값: 5)')
    parser.add_argument('--interactive', action='store_true', help='대화형 모드로 실행')
    parser.add_argument('--verbose', action='store_true', help='상세 출력 모드')
    parser.add_argument('--save-file', help='결과 저장 파일명 (기본값: 자동 생성)')

    return parser.parse_args()


def validate_config(config_dict):
    """설정 유효성 검사"""
    errors = []

    if not config_dict.get('environment'):
        errors.append("환경(environment)을 지정해주세요.")

    if not config_dict.get('count') or config_dict['count'] <= 0:
        errors.append("계정 수(count)는 1 이상이어야 합니다.")

    if config_dict.get('environment') == 'real' and not config_dict.get('base_email'):
        errors.append("Real 환경에서는 기본 이메일(base_email)이 필요합니다.")

    if config_dict.get('delay', 0) < 0:
        errors.append("생성 간격(delay)은 0 이상이어야 합니다.")

    return errors


async def main():
    """메인 함수"""
    args = parse_arguments()

    print("위버스 계정 자동화 프로그램")
    print("=" * 60)

    # 설정 수집
    if args.interactive or not args.env or not args.count:
        print("대화형 모드로 실행됩니다.\n")
        config_dict = get_user_input()
    else:
        config_dict = {
            'environment': args.env,
            'count': args.count,
            'base_email': args.base_email,
            'custom_password': args.password,
            'custom_nickname': args.nickname,
            'delay': args.delay,
            # 슬랙 설정 고정
            'slack_webhook_url': "https://hooks.slack.com/services/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",
            'gmail_account': {
                "email": "weversetestmail@gmail.com",
                "password": "not_needed_for_api"
            }
        }

    # 설정 유효성 검사
    validation_errors = validate_config(config_dict)
    if validation_errors:
        print("❌ 설정 오류:")
        for error in validation_errors:
            print(f"  - {error}")
        return 1

    # 설정 확인
    print(f"\n📋 설정 확인:")
    print(f"환경: {config_dict['environment'].upper()}")
    print(f"계정 수: {config_dict['count']}개")
    if config_dict['environment'] == 'real':
        print(f"이메일 방식: Gmail dot 방식")
        print(f"기본 이메일: {config_dict['base_email']}")
    else:
        print(f"이메일 방식: @benx.com 랜덤 생성")

    if config_dict['custom_password']:
        print(f"비밀번호: 사용자 지정")
    if config_dict['custom_nickname']:
        print(f"닉네임: {config_dict['custom_nickname']}")

    print(f"생성 간격: {config_dict['delay']}초")
    print(f"Slack 알림: 활성화 (고정)")  # 고정 표시

    # 진행 확인
    if not args.interactive:
        confirm = input("\n계속 진행하시겠습니까? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("취소되었습니다.")
            return 0

    try:
        # 계정 생성 설정 객체 생성
        config = AccountCreationConfig(**config_dict)

        # 계정 생성기 초기화
        creator = WeverseAccountCreator(config)

        print(f"\n🎯 계정 생성을 시작합니다...")

        # 계정 생성 실행
        accounts = await creator.create_multiple_accounts()

        # 결과 출력
        if args.verbose:
            print_account_details(accounts)

        # 결과 파일 저장
        saved_file = creator.save_results(args.save_file)

        # 통계 정보
        stats = creator.get_statistics()
        print(f"\n최종 통계:")
        print(f"성공률: {stats['success_rate']:.1f}% ({stats['success']}/{stats['total']})")
        print(f"결과 파일: {saved_file}")

        # 성공한 계정이 있으면 성공 코드, 모두 실패하면 실패 코드
        return 0 if stats['success'] > 0 else 1

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        return 130

    except Exception as e:
        print(f"\n오류 발생: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    # 비동기 실행
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n프로그램이 중단되었습니다.")
        sys.exit(130)