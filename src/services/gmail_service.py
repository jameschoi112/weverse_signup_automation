"""
Gmail API 서비스
"""
import asyncio
import base64
import re
import os
import pickle
import time
from datetime import datetime
from typing import Optional, Dict, Any
from config.settings import GMAIL_SETTINGS


class GmailService:
    """Gmail API를 이용한 메일 서비스"""

    def __init__(self, credentials_file: str = None, token_file: str = None):
        self.credentials_file = credentials_file or GMAIL_SETTINGS["credentials_file"]
        self.token_file = token_file or GMAIL_SETTINGS["token_file"]
        self.service = None

    async def initialize(self) -> bool:
        """Gmail API 서비스 초기화"""
        try:
            self.service = await self._get_gmail_service()
            return self.service is not None
        except Exception as e:
            print(f"[ERROR] Gmail 서비스 초기화 실패: {e}")
            return False

    async def find_verification_email(self, target_email: str, max_wait_minutes: int = 2) -> Optional[str]:
        """인증 메일에서 링크 찾기"""
        if not self.service:
            print("[ERROR] Gmail 서비스가 초기화되지 않았습니다")
            return None

        print(f"[GMAIL API] 인증 메일 검색 중... (최대 {max_wait_minutes}분 대기)")

        max_attempts = max_wait_minutes * 12  # 5초마다 체크
        latest_link = None
        latest_timestamp = 0

        for attempt in range(max_attempts):
            try:
                # 위버스 관련 메일 검색
                query = "from:weverse OR from:hybe OR subject:weverse OR subject:인증 OR subject:verification"
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=10
                ).execute()

                messages = results.get('messages', [])

                for message in messages:
                    try:
                        msg = self.service.users().messages().get(
                            userId='me',
                            id=message['id'],
                            format='full'
                        ).execute()

                        # 메일 수신 시간 확인
                        internal_date = int(msg['internalDate']) / 1000

                        # 현재 시간 기준 5분 이내의 메일만 처리
                        current_time = time.time()
                        if current_time - internal_date > 300:  # 5분 = 300초
                            continue

                        verification_link = self._extract_verification_link(msg)
                        if verification_link:
                            # 더 최신 메일인 경우에만 업데이트
                            if internal_date > latest_timestamp:
                                latest_link = verification_link
                                latest_timestamp = internal_date

                    except Exception as e:
                        print(f"[DEBUG] 메시지 처리 중 오류: {e}")
                        continue

                # 최신 링크를 찾았으면 바로 반환
                if latest_link:
                    print(f"[GMAIL API] 인증 링크 발견!")
                    return latest_link

            except Exception as e:
                print(f"[DEBUG] Gmail API 검색 오류: {e}")

            print(f"[GMAIL API] 인증 메일 대기 중... ({attempt + 1}/{max_attempts})")
            await asyncio.sleep(5)

        print("[GMAIL API] 인증 메일을 찾지 못했습니다.")
        return None

    async def find_verification_code_after_time(self, target_email: str, after_timestamp: float) -> Optional[str]:
        """특정 시점 이후 도착한 인증 코드 검색 (개선된 버전)"""
        if not self.service:
            return None

        print(f"[GMAIL API] {datetime.fromtimestamp(after_timestamp).strftime('%H:%M:%S')} 이후 인증 코드 검색 중...")

        for attempt in range(24):  # 5초마다 체크, 최대 2분
            try:
                query = "from:noreply@weverse.io subject:이메일 인증을 완료해주세요"
                results = self.service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=10
                ).execute()

                messages = results.get('messages', [])
                valid_codes = []

                for message in messages:
                    try:
                        msg = self.service.users().messages().get(
                            userId='me',
                            id=message['id'],
                            format='full'
                        ).execute()

                        # 메일 수신 시간 확인
                        internal_date = int(msg['internalDate']) / 1000

                        # 시간 여유를 더 크게 줌 (120초 = 2분)
                        time_buffer = 120

                        # 요청 시점보다 2분 이전까지의 메일도 포함
                        if internal_date >= after_timestamp - time_buffer:
                            verification_code = self._extract_verification_code(msg)
                            if verification_code:
                                mail_time = datetime.fromtimestamp(internal_date)
                                print(f"[FOUND] 인증 코드 발견: {verification_code} (수신: {mail_time.strftime('%H:%M:%S')})")
                                valid_codes.append((internal_date, verification_code))
                        else:
                            mail_time = datetime.fromtimestamp(internal_date)
                            print(f"[SKIP] 너무 오래된 메일 건너뛰기 (수신: {mail_time.strftime('%H:%M:%S')})")

                    except Exception:
                        continue

                # 가장 최신 코드 반환
                if valid_codes:
                    valid_codes.sort(key=lambda x: x[0], reverse=True)
                    latest_time, latest_code = valid_codes[0]
                    mail_time = datetime.fromtimestamp(latest_time)
                    print(f"[SUCCESS] 최신 인증 코드 선택: {latest_code} (수신: {mail_time.strftime('%H:%M:%S')})")
                    return latest_code

            except Exception as e:
                print(f"[DEBUG] Gmail API 검색 오류: {e}")

            print(f"[GMAIL API] 인증 코드 대기 중... ({attempt + 1}/24)")
            await asyncio.sleep(5)

        print("[GMAIL API] 인증 코드를 찾지 못했습니다.")
        return None

    async def get_latest_verification_code(self, target_email: str = None) -> Optional[str]:
        """가장 최근 인증 코드 가져오기 (시간 제한 없음)"""
        if not self.service:
            return None

        print(f"[GMAIL API] 최신 인증 코드 검색 중...")

        try:
            query = "from:noreply@weverse.io subject:이메일 인증을 완료해주세요"
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5  # 최근 5개만 확인
            ).execute()

            messages = results.get('messages', [])
            codes_with_time = []

            for message in messages:
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=message['id'],
                        format='full'
                    ).execute()

                    # 메일 수신 시간 확인
                    internal_date = int(msg['internalDate']) / 1000

                    # 인증 코드 추출
                    verification_code = self._extract_verification_code(msg)
                    if verification_code:
                        mail_time = datetime.fromtimestamp(internal_date)
                        print(f"[FOUND] 인증 코드: {verification_code} (수신: {mail_time.strftime('%H:%M:%S')})")
                        codes_with_time.append((internal_date, verification_code))

                except Exception:
                    continue

            # 가장 최신 코드 반환
            if codes_with_time:
                codes_with_time.sort(key=lambda x: x[0], reverse=True)
                latest_time, latest_code = codes_with_time[0]
                mail_time = datetime.fromtimestamp(latest_time)
                print(f"[SUCCESS] 최신 인증 코드: {latest_code} (수신: {mail_time.strftime('%H:%M:%S')})")
                return latest_code

        except Exception as e:
            print(f"[ERROR] 최신 인증 코드 검색 실패: {e}")

        return None

    async def _get_gmail_service(self):
        """Gmail API 서비스 객체 생성"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import Flow
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request

            creds = None

            # 저장된 토큰 확인
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)

            # 토큰이 없거나 만료된 경우 새로 인증
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_file):
                        print(f"[ERROR] {self.credentials_file} 파일이 없습니다.")
                        print("[INFO] Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하세요.")
                        return None

                    flow = Flow.from_client_secrets_file(self.credentials_file, GMAIL_SETTINGS["scopes"])
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

                    auth_url, _ = flow.authorization_url(prompt='consent')
                    print(f"[AUTH] 다음 URL에서 인증하세요: {auth_url}")
                    code = input('[INPUT] 인증 코드를 입력하세요: ')

                    flow.fetch_token(code=code)
                    creds = flow.credentials

                # 토큰 저장
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)

            # Gmail API 서비스 생성
            return build('gmail', 'v1', credentials=creds)

        except ImportError:
            print("[ERROR] Google API 라이브러리가 설치되지 않았습니다.")
            print("[INFO] 다음 명령어로 설치하세요: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return None
        except Exception as e:
            print(f"[ERROR] Gmail API 서비스 생성 실패: {e}")
            return None

    def _extract_verification_link(self, msg: Dict[str, Any]) -> Optional[str]:
        """Gmail 메시지에서 인증 링크 추출"""
        try:
            body = self._extract_email_body(msg)

            # 1. 이메일 인증 버튼 텍스트 주변에서 링크 찾기
            email_verification_patterns = [
                r'<a[^>]*href="([^"]*)"[^>]*>[^<]*이메일\s*인증[^<]*</a>',
                r'<a[^>]*href="([^"]*)"[^>]*>[^<]*인증[^<]*</a>',
                r'<a[^>]*href="([^"]*)"[^>]*>[^<]*verification[^<]*</a>',
                r'<a[^>]*href="([^"]*)"[^>]*>[^<]*confirm[^<]*</a>',
            ]

            for pattern in email_verification_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE | re.DOTALL)
                if matches:
                    link = matches[0].replace('&amp;', '&')
                    print(f"[SUCCESS] 이메일 인증 버튼 링크 발견: {link}")
                    return link

            # 2. 위버스 도메인 링크 패턴으로 찾기
            weverse_link_patterns = [
                r'https://account\.weverse\.io/signup-complete[^"\s]*',
                r'https://[^"\s]*weverse[^"\s]*signup-complete[^"\s]*',
                r'https://[^"\s]*weverse[^"\s]*verify[^"\s]*',
                r'https://[^"\s]*weverse[^"\s]*confirm[^"\s]*',
                r'https://[^"\s]*weverse[^"\s]*auth[^"\s]*',
                r'https://account\.weverse\.io[^"\s]*key=[^"\s]*',
            ]

            for pattern in weverse_link_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    link = matches[0].replace('&amp;', '&')
                    print(f"[SUCCESS] 위버스 도메인 링크 발견: {link}")
                    return link

            # 3. data-saferedirecturl에서 링크 추출 (Google에서 리다이렉트 URL)
            redirect_patterns = [
                r'data-saferedirecturl="[^"]*url\?q=([^"&]*)',
                r'https://www\.google\.com/url\?q=([^"&]*)',
            ]

            for pattern in redirect_patterns:
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    import urllib.parse
                    link = urllib.parse.unquote(matches[0])
                    if 'weverse' in link.lower() and (
                            'signup-complete' in link.lower() or 'verify' in link.lower() or 'key=' in link.lower()):
                        print(f"[SUCCESS] Google 리다이렉트에서 위버스 링크 발견: {link}")
                        return link

            # 4. 모든 링크를 추출해서 위버스 관련인지 확인 (최후 수단)
            all_links = re.findall(r'href="([^"]*)"', body, re.IGNORECASE)
            for link in all_links:
                clean_link = link.replace('&amp;', '&')
                if ('weverse' in clean_link.lower() and
                        ('signup-complete' in clean_link.lower() or 'verify' in clean_link.lower() or
                         'confirm' in clean_link.lower() or 'key=' in clean_link.lower())):
                    print(f"[SUCCESS] 모든 링크 검사에서 위버스 링크 발견: {clean_link}")
                    return clean_link

            print("[WARNING] 인증 링크를 찾을 수 없습니다.")
            return None

        except Exception as e:
            print(f"[ERROR] 인증 링크 추출 실패: {e}")
            return None

    def _extract_verification_code(self, msg: Dict[str, Any]) -> Optional[str]:
        """Gmail 메시지에서 6자리 인증 코드 추출"""
        try:
            body = self._extract_email_body(msg)

            # 6자리 숫자 코드 패턴 찾기
            code_patterns = [
                r'인증 코드(\s*)?(\d{6})',
                r'(\d{6})',
                r'>(\d{6})<',
                r'코드[^\d]*(\d{6})',
            ]

            for pattern in code_patterns:
                matches = re.findall(pattern, body)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            code = match[-1] if len(match) > 1 else match[0]
                        else:
                            code = match

                        if code and len(code) == 6 and code.isdigit():
                            return code

            return None

        except Exception as e:
            print(f"[ERROR] 인증 코드 추출 실패: {e}")
            return None

    def _extract_email_body(self, msg: Dict[str, Any]) -> str:
        """이메일 본문 추출"""
        body = ""
        payload = msg.get('payload', {})

        # multipart 메시지 처리
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] in ['text/html', 'text/plain']:
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # 단일 part 메시지
            data = payload['body'].get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body