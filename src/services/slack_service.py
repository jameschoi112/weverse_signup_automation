"""
Slack 알림 서비스
"""
import asyncio
import ssl
from datetime import datetime
from typing import Optional
import aiohttp
from config.settings import SLACK_SETTINGS
from models.account import AccountInfo


class SlackService:
    """Slack 웹훅을 이용한 알림 서비스"""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url or SLACK_SETTINGS["default_webhook_url"]
        self.timeout = SLACK_SETTINGS["timeout"]

    async def send_verification_link(self, verification_link: str, email: str) -> bool:
        """인증 링크를 클릭 가능한 버튼으로 전송"""
        if not self.webhook_url:
            print(f"[SLACK] 인증 링크: {verification_link}")
            return False

        try:
            slack_data = {
                "text": "🔔 위버스 이메일 인증이 필요합니다!",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*[이메일 인증 요청]*\n\n"
                                    f"계정: `{email}`\n"
                                    f"아래 버튼을 클릭하여 이메일 인증을 완료해주세요."
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "이메일 인증하기",
                                    "emoji": True
                                },
                                "style": "primary",
                                "url": verification_link,
                                "action_id": "email_verification"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"요청 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            success = await self._send_message(slack_data)
            if success:
                print(f"[SLACK] 인증 링크 전송 성공: {email}")
                print(f"[SLACK] 버튼 클릭으로 인증을 완료해주세요!")

            return success

        except Exception as e:
            print(f"[SLACK] 인증 링크 전송 중 오류: {e}")
            return False

    async def send_notification(self, message: str, account_info: AccountInfo) -> bool:
        """일반 알림 발송"""
        if not self.webhook_url:
            print(f"[SLACK] {message}")
            return False

        try:
            slack_data = {
                "text": "🔔 위버스 계정 생성 알림",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{message}*\n\n"
                                    f"이메일: `{account_info.email}`\n"
                                    f"비밀번호: `{account_info.password}`\n"
                                    f"닉네임: `{account_info.nickname}`\n"
                                    f"환경: `{account_info.environment.upper()}`\n"
                                    f"생성시간: `{account_info.created_at}`"
                        }
                    }
                ]
            }

            success = await self._send_message(slack_data)
            if success:
                print(f"[SLACK] 알림 발송 성공: {account_info.email}")

            return success

        except Exception as e:
            print(f"[SLACK] 알림 발송 중 오류: {e}")
            return False

    async def send_success_notification(self, account_info: AccountInfo) -> bool:
        """계정 생성 성공 알림"""
        message = "계정 생성 완료"

        if not self.webhook_url:
            print(f"[SLACK] {message}: {account_info.email}")
            return False

        try:
            slack_data = {
                "text": "✅ 위버스 계정 생성 완료!",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "[계정 생성 완료]"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*ID(이메일):*\n`{account_info.email}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*PW:*\n`{account_info.password}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*WID:*\n`{account_info.wid or 'N/A'}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*환경:*\n`{account_info.environment.upper()}`"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*완료시간:*\n`{account_info.updated_at}`"
                            }
                        ]
                    }
                ]
            }

            success = await self._send_message(slack_data)
            if success:
                print(f"[SLACK] 성공 알림 발송: {account_info.email}")

            return success

        except Exception as e:
            print(f"[SLACK] 성공 알림 발송 중 오류: {e}")
            return False

    async def send_error_notification(self, error_message: str, account_info: AccountInfo) -> bool:
        """에러 알림 발송"""
        if not self.webhook_url:
            print(f"[SLACK] ERROR: {error_message}")
            return False

        try:
            slack_data = {
                "text": "❌ 위버스 계정 생성 실패",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "❌ 계정 생성 실패"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*오류 내용:*\n{error_message}\n\n"
                                    f"*계정 정보:*\n"
                                    f"이메일: `{account_info.email}`\n"
                                    f"상태: `{account_info.status}`\n"
                                    f"환경: `{account_info.environment.upper()}`"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"실패 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            success = await self._send_message(slack_data)
            if success:
                print(f"[SLACK] 에러 알림 발송: {account_info.email}")

            return success

        except Exception as e:
            print(f"[SLACK] 에러 알림 발송 중 오류: {e}")
            return False

    async def send_bulk_summary(self, total_count: int, success_count: int, failed_count: int,
                                environment: str) -> bool:
        """일괄 생성 결과 요약 알림"""
        if not self.webhook_url:
            return False

        try:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0

            # 성공률에 따른 이모지 선택
            if success_rate == 100:
                status_emoji = "🎉"
                status_text = "완벽!"
            elif success_rate >= 80:
                status_emoji = "✅"
                status_text = "성공"
            elif success_rate >= 50:
                status_emoji = "⚠️"
                status_text = "부분 성공"
            else:
                status_emoji = "❌"
                status_text = "실패"

            slack_data = {
                "text": f"{status_emoji} 위버스 계정 일괄 생성 완료",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{status_emoji} 일괄 생성 {status_text}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*총 시도:*\n{total_count}개"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*성공:*\n{success_count}개"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*실패:*\n{failed_count}개"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*성공률:*\n{success_rate:.1f}%"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*환경:*\n{environment.upper()}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*완료시간:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        ]
                    }
                ]
            }

            success = await self._send_message(slack_data)
            if success:
                print(f"[SLACK] 일괄 생성 요약 알림 발송 완료")

            return success

        except Exception as e:
            print(f"[SLACK] 요약 알림 발송 중 오류: {e}")
            return False

    async def _send_message(self, slack_data: dict) -> bool:
        """Slack 메시지 전송"""
        try:
            # SSL 인증서 검증 비활성화
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
            ) as session:
                async with session.post(self.webhook_url, json=slack_data) as response:
                    return response.status == 200

        except Exception as e:
            print(f"[SLACK] 메시지 전송 실패: {e}")
            return False

    def set_webhook_url(self, webhook_url: str) -> None:
        """웹훅 URL 설정"""
        self.webhook_url = webhook_url