"""
위버스 웹사이트 조작 서비스
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Optional
from playwright.async_api import Page, Browser
from config.settings import WEVERSE_URLS, BROWSER_SETTINGS
from models.account import AccountInfo, AccountStatus


class WeverseService:
    """위버스 웹사이트 조작 서비스"""

    def __init__(self):
        self.base_url = WEVERSE_URLS["signup"]
        self.login_url = WEVERSE_URLS["login"]
        self.timeout = BROWSER_SETTINGS["timeout"]
        self.wait_timeout = BROWSER_SETTINGS["wait_timeout"]

    async def fill_signup_form(self, page: Page, account_info: AccountInfo) -> bool:
        """회원가입 폼 전체 작성"""
        try:
            # 회원가입 페이지 접속
            await page.goto(self.base_url)
            print(f"[WEVERSE] 회원가입 페이지 접속: {account_info.email}")

            # 1. 이메일 입력 단계
            if not await self._fill_email_step(page, account_info.email):
                account_info.update_status(AccountStatus.EMAIL_STEP_FAILED)
                return False

            # 2. 비밀번호 설정 단계
            if not await self._fill_password_step(page, account_info.password):
                account_info.update_status(AccountStatus.PASSWORD_STEP_FAILED)
                return False

            # 3. 닉네임 설정 단계
            if not await self._fill_nickname_step(page, account_info.nickname):
                account_info.update_status(AccountStatus.NICKNAME_STEP_FAILED)
                return False

            # 4. 약관 동의 단계
            if not await self._fill_terms_step(page):
                account_info.update_status(AccountStatus.TERMS_STEP_FAILED)
                return False

            # 이메일 인증 대기 상태로 변경
            account_info.update_status(AccountStatus.EMAIL_VERIFICATION_PENDING)
            print(f"[WEVERSE] 회원가입 폼 작성 완료: {account_info.email}")
            return True

        except Exception as e:
            print(f"[ERROR] 회원가입 폼 작성 실패: {e}")
            account_info.update_status(AccountStatus.CREATION_FAILED)
            return False

    async def login_and_extract_wid(self, page: Page, account_info: AccountInfo, is_multi_account: bool = False) -> bool:
        """로그인 후 마이페이지에서 WID 추출"""
        try:
            print(f"[WEVERSE] 로그인 시작: {account_info.email}")

            # 로그인 페이지로 이동
            await page.goto(self.login_url)
            await asyncio.sleep(3)

            # 이메일 입력
            email_input = await page.wait_for_selector('input[name="email"]', timeout=self.wait_timeout)
            await email_input.fill(account_info.email)
            print(f"[WEVERSE] 이메일 입력 완료")

            # 비밀번호 입력
            password_input = await page.wait_for_selector('input[name="password"]', timeout=self.wait_timeout)
            await password_input.fill(account_info.password)
            print(f"[WEVERSE] 비밀번호 입력 완료")

            # 로그인 버튼 클릭
            login_button = await page.wait_for_selector('span:has-text("로그인")', timeout=self.wait_timeout)
            await login_button.click()
            print("[WEVERSE] 로그인 버튼 클릭 완료")

            # 추가 인증 처리 (필요한 경우)
            additional_auth_needed = await self._handle_additional_verification_check(page)
            if additional_auth_needed:
                return False  # 추가 인증이 필요하면 상위에서 처리하도록 반환

            # 로그인 완료 대기
            await asyncio.sleep(5)

            # 마이페이지로 이동해서 WID 추출
            wid_success = await self._go_to_mypage_and_extract_wid(page, account_info)

            if wid_success:
                print(f"[SUCCESS] WID 추출 완료: {account_info.wid}")
                account_info.update_status(AccountStatus.COMPLETED)

                # 다중 계정인 경우 로그아웃 처리
                if is_multi_account:
                    await self._logout_for_next_account(page)

                return True
            else:
                print(f"[WARNING] WID 추출 실패")
                account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)
                return False

        except Exception as e:
            print(f"[ERROR] 로그인 및 WID 추출 실패: {e}")
            account_info.update_status(AccountStatus.WID_EXTRACTION_FAILED)
            return False

    async def _go_to_mypage_and_extract_wid(self, page: Page, account_info: AccountInfo) -> bool:
        """마이페이지로 이동해서 WID 추출"""
        try:
            print("[WEVERSE] 마이페이지로 이동 중...")

            # API 응답 감지를 위한 리스너 설정
            def handle_response(response):
                try:
                    # users/me 또는 users/account/me API 모두 체크
                    if ('users/v1.0/users/me' in response.url or 'users/v1.0/users/account/me' in response.url) and response.status == 200:
                        asyncio.create_task(self._extract_wid_from_response(response, account_info))
                except Exception as e:
                    print(f"[DEBUG] API 응답 처리 중 오류: {e}")

            page.on('response', handle_response)

            # 마이페이지 버튼 클릭 (HTML 기반으로 업데이트)
            try:
                # 마이페이지 버튼 찾기 (여러 방법 시도)
                mypage_selectors = [
                    'button.HeaderView_profile_button__wmSNK',  # HTML에서 확인된 실제 클래스
                    'svg[width="38"][height="38"]',  # SVG 크기 기준
                    'button:has(svg[width="38"][height="38"])',  # SVG를 포함한 버튼
                    'path[d*="M19.0175 31.8641"]',  # 새로운 path 기준
                    'button:has(path[d*="M19.0175 31.8641"])',  # 새로운 path를 포함한 버튼
                    '[aria-label*="마이"] button',  # aria-label 기준
                    '[title*="마이"] button',  # title 기준
                    'button:has(path[stroke="currentColor"])',  # SVG path 기준
                ]

                mypage_button_found = False
                for selector in mypage_selectors:
                    try:
                        mypage_button = await page.wait_for_selector(selector, timeout=5000)
                        if mypage_button:
                            print(f"[WEVERSE] 마이페이지 버튼 발견: {selector}")
                            await mypage_button.click()
                            print("[WEVERSE] 마이페이지 버튼 클릭 완료")
                            mypage_button_found = True
                            break
                    except Exception as e:
                        print(f"[DEBUG] 셀렉터 {selector} 실패: {e}")
                        continue

                if not mypage_button_found:
                    # 마지막 시도: 헤더의 우상단 버튼들 중에서 찾기
                    print("[WEVERSE] 다른 방법으로 마이페이지 접근 시도...")
                    try:
                        # 헤더의 프로필 관련 버튼들 시도
                        header_buttons = await page.query_selector_all('header button')
                        for i, button in enumerate(header_buttons):
                            try:
                                # 버튼 내용 확인
                                button_content = await button.inner_text()
                                button_class = await button.get_attribute('class')
                                print(f"[DEBUG] 헤더 버튼 {i}: class={button_class}, text='{button_content}'")

                                # 프로필 관련 버튼 찾기
                                if ('profile' in str(button_class).lower() or
                                    'HeaderView_profile_button' in str(button_class)):
                                    await button.click()
                                    print(f"[WEVERSE] 프로필 버튼 클릭 완료 (인덱스: {i})")
                                    mypage_button_found = True
                                    break
                            except:
                                continue

                        if not mypage_button_found:
                            raise Exception("마이페이지 버튼을 찾을 수 없음")

                    except Exception as e:
                        print(f"[WARNING] 마이페이지 버튼 클릭 실패: {e}")
                        # 직접 마이페이지 URL로 이동 시도
                        await page.goto("https://weverse.io/more")
                        print("[WEVERSE] 직접 마이페이지 URL로 이동")

            except Exception as e:
                print(f"[WARNING] 마이페이지 버튼 클릭 실패: {e}")
                # 직접 마이페이지 URL로 이동 시도
                await page.goto("https://weverse.io/more")
                print("[WEVERSE] 직접 마이페이지 URL로 이동")

            # 마이페이지 로딩 대기 및 확인
            await asyncio.sleep(5)

            # 현재 URL 확인
            current_url = page.url
            print(f"[WEVERSE] 현재 페이지 URL: {current_url}")

            # 마이페이지에 도달했는지 확인
            if '/more' not in current_url and 'weverse.io' in current_url:
                print("[WARNING] 마이페이지로 이동하지 못함 - 다시 시도")
                try:
                    await page.goto("https://weverse.io/more")
                    await asyncio.sleep(3)
                    print("[WEVERSE] 강제로 마이페이지 URL 이동 완료")
                except:
                    print("[ERROR] 마이페이지 이동 실패")
                    return False

            # WID 추출 대기 (최대 20초)
            print("[WEVERSE] 마이페이지에서 WID 추출 대기 중...")
            for i in range(20):
                await asyncio.sleep(1)
                if account_info.wid:
                    print(f"[SUCCESS] 마이페이지에서 WID 추출 완료: {account_info.wid}")
                    return True

            print(f"[WARNING] 마이페이지에서 WID 추출 실패")
            return False

        except Exception as e:
            print(f"[ERROR] 마이페이지 WID 추출 실패: {e}")
            return False

    async def _logout_for_next_account(self, page: Page):
        """다음 계정을 위한 로그아웃 처리"""
        try:
            print("[WEVERSE] 다음 계정을 위해 로그아웃 중...")

            # 로그아웃 버튼 찾기 및 클릭
            logout_selectors = [
                'button.MoreHeaderView_sign_out__WEhHK',  # 정확한 클래스명
                'button:has-text("로그아웃")',  # 텍스트 기준
                '[class*="sign_out"] button',  # 클래스 부분 매칭
                'button[type="button"]:has-text("로그아웃")',  # 타입과 텍스트 조합
            ]

            logout_success = False
            for selector in logout_selectors:
                try:
                    logout_button = await page.wait_for_selector(selector, timeout=5000)
                    if logout_button:
                        await logout_button.click()
                        print("[WEVERSE] 로그아웃 버튼 클릭 완료")
                        logout_success = True
                        break
                except:
                    continue

            if not logout_success:
                print("[WARNING] 로그아웃 버튼을 찾을 수 없음 - 수동 처리 필요")
            else:
                # 로그아웃 완료 대기
                await asyncio.sleep(3)
                print("[WEVERSE] 로그아웃 완료 - 다음 계정 준비됨")

        except Exception as e:
            print(f"[ERROR] 로그아웃 처리 실패: {e}")

    async def _handle_additional_verification_check(self, page: Page) -> bool:
        """추가 인증이 필요한지 확인만 (처리는 상위에서)"""
        try:
            await asyncio.sleep(3)  # 로그인 처리 대기

            # 비정상적인 접근 메시지 확인
            abnormal_access_message = await page.query_selector('li:has-text("비정상적인 접근으로 감지되어, 인증이 필요합니다.")')
            if abnormal_access_message:
                print("[INFO] 비정상적인 접근 감지 - 추가 인증 필요")
                return True

            # OTP 코드 입력 필드가 있는지도 확인
            otp_field = await page.query_selector('input#otpCode')
            if otp_field:
                print("[INFO] OTP 입력 필드 발견 - 추가 인증 필요")
                return True

            print("[INFO] 추가 인증이 필요하지 않음 - 정상 로그인")
            return False

        except Exception as e:
            print(f"[INFO] 추가 인증 확인 중 오류 (정상 로그인으로 가정): {e}")
            return False

    async def handle_additional_verification_and_extract_wid(self, page: Page, account_info: AccountInfo,
                                                           gmail_service, is_multi_account: bool = False) -> bool:
        """추가 인증 처리 후 WID 추출"""
        try:
            # 인증 코드 요청 시점 기록
            code_request_time = time.time()
            print(f"[INFO] 인증 코드 요청 시점: {datetime.fromtimestamp(code_request_time).strftime('%H:%M:%S')}")

            # 잠시 대기 후 Gmail에서 인증 코드 확인
            print("[INFO] 새로운 인증 코드 도착 대기 중... (10초)")
            await asyncio.sleep(10)

            # Gmail에서 최신 인증 코드 확인
            verification_code = await gmail_service.get_latest_verification_code(account_info.email)

            if verification_code:
                print(f"[INFO] 인증 코드 발견: {verification_code}")

                # 인증 코드 입력
                code_input_success = await self.input_verification_code(page, verification_code)

                if code_input_success:
                    # 인증 완료 후 마이페이지에서 WID 추출
                    await asyncio.sleep(5)

                    wid_success = await self._go_to_mypage_and_extract_wid(page, account_info)

                    if wid_success:
                        account_info.update_status(AccountStatus.COMPLETED)

                        # 다중 계정인 경우 로그아웃 처리
                        if is_multi_account:
                            await self._logout_for_next_account(page)

                        return True
                    else:
                        print("[WARNING] 추가 인증 후 WID 추출 실패")
                        return False
                else:
                    print("[ERROR] 인증 코드 입력 실패")
                    return False
            else:
                print("[WARNING] 추가 인증 코드를 찾을 수 없음")
                return False

        except Exception as e:
            print(f"[ERROR] 추가 인증 처리 실패: {e}")
            return False

    async def _fill_email_step(self, page: Page, email: str) -> bool:
        """이메일 입력 단계"""
        try:
            print(f"[STEP 1] 이메일 입력: {email}")

            await page.wait_for_load_state('networkidle')

            # 이메일 입력
            await page.wait_for_selector('input[name="userEmail"]', timeout=self.wait_timeout)
            await page.fill('input[name="userEmail"]', email)

            # 이메일로 계속하기 버튼 클릭
            await page.wait_for_selector('span:has-text("이메일로 계속하기")', timeout=self.wait_timeout)
            await page.click('span:has-text("이메일로 계속하기")')

            # 가입하기 버튼 대기 및 클릭
            try:
                await page.wait_for_selector('span:has-text("가입하기")', timeout=self.wait_timeout)
                await page.click('span:has-text("가입하기")')
                return True
            except:
                # 오류 메시지 확인
                error_elements = await page.query_selector_all('text="유효한 이메일을 입력해 주세요."')
                if error_elements:
                    print(f"[ERROR] 이메일 형식 오류: {email}")
                    return False

                # 이미 가입된 이메일 확인 - 수정된 셀렉터
                try:
                    # 텍스트로 직접 찾기
                    existing_text = await page.query_selector('text="이미 가입된"')
                    if existing_text:
                        print(f"[WARNING] 이미 가입된 이메일: {email}")
                        return False

                    # 다른 방법으로도 시도
                    existing_elements = await page.query_selector_all('div:has-text("이미 가입된")')
                    if existing_elements:
                        print(f"[WARNING] 이미 가입된 이메일: {email}")
                        return False
                except:
                    pass

                raise Exception("알 수 없는 오류")

        except Exception as e:
            print(f"[ERROR] 이메일 입력 단계 실패: {e}")
            return False

    async def _fill_password_step(self, page: Page, password: str) -> bool:
        """비밀번호 설정 단계"""
        try:
            print(f"[STEP 2] 비밀번호 설정")

            # 비밀번호 입력 필드 대기
            await page.wait_for_selector('input[name="newPassword"]', timeout=self.wait_timeout)

            # 새 비밀번호 입력
            await page.fill('input[name="newPassword"]', password)
            await page.fill('input[name="confirmPassword"]', password)

            # 비밀번호 입력 후 잠시 대기 (유효성 검사 시간)
            await asyncio.sleep(1)

            # 다음 버튼 클릭
            await page.wait_for_selector('span:has-text("다음")', timeout=self.wait_timeout)
            await page.click('span:has-text("다음")')

            print("[INFO] 비밀번호 설정 완료 및 다음 단계로 이동")
            return True

        except Exception as e:
            print(f"[ERROR] 비밀번호 설정 단계 실패: {e}")
            return False

    async def _fill_nickname_step(self, page: Page, nickname: str) -> bool:
        """닉네임 설정 단계"""
        try:
            print(f"[STEP 3] 닉네임 설정: {nickname}")

            # 닉네임 필드 대기 및 입력
            await page.wait_for_selector('input[name="nickname"]', timeout=self.wait_timeout)

            # 기본 닉네임 지우고 새 닉네임 입력
            await page.fill('input[name="nickname"]', "")
            await page.fill('input[name="nickname"]', nickname)

            # 다음 버튼 클릭
            await page.click('span:has-text("다음")')

            return True

        except Exception as e:
            print(f"[ERROR] 닉네임 설정 단계 실패: {e}")
            return False

    async def _fill_terms_step(self, page: Page) -> bool:
        """약관 동의 단계"""
        try:
            print(f"[STEP 4] 약관 동의")

            # 약관 동의 페이지 대기
            await page.wait_for_selector('span:has-text("모두 동의 합니다.")', timeout=self.wait_timeout)

            # 모두 동의 체크박스 클릭
            await page.click('span:has-text("모두 동의 합니다.")')

            # 다음 버튼 클릭
            await page.click('span:has-text("다음")')

            # 광고 수신 동의 팝업 처리
            try:
                print("[INFO] 광고 수신 동의 팝업 대기 중...")
                await page.wait_for_selector('button.sc-c96a04fb-9.dtbJuX:has-text("확인")', timeout=8000)
                await page.click('button.sc-c96a04fb-9.dtbJuX:has-text("확인")')
                print("[INFO] 광고 수신 동의 팝업 처리 완료")
                await asyncio.sleep(2)

            except Exception as popup_error:
                print(f"[WARNING] 광고 수신 팝업 처리 실패: {popup_error}")
                try:
                    await page.click('button:has-text("확인")')
                    print("[INFO] 대체 방식으로 팝업 처리 완료")
                    await asyncio.sleep(2)
                except:
                    print("[INFO] 광고 수신 동의 팝업 없음 또는 이미 처리됨")

            return True

        except Exception as e:
            print(f"[ERROR] 약관 동의 단계 실패: {e}")
            return False

    async def input_verification_code(self, page: Page, verification_code: str) -> bool:
        """인증 코드 입력"""
        try:
            print(f"[INFO] 인증 코드 입력: {verification_code}")

            # 인증 코드 입력
            otp_input = await page.wait_for_selector('input#otpCode', timeout=self.wait_timeout)
            await otp_input.fill(verification_code)
            print("[INFO] 인증 코드 입력 완료")

            # 인증 코드 확인 버튼 클릭
            try:
                confirm_button = await page.wait_for_selector('span:has-text("확인")', timeout=5000)
                await confirm_button.click()
                print("[INFO] 인증 코드 확인 버튼 클릭 완료")
            except:
                # Enter 키로 인증 시도
                await otp_input.press('Enter')
                print("[INFO] Enter 키로 인증 코드 제출")

            await asyncio.sleep(3)  # 인증 처리 대기

            # 로그인 완료 팝업 처리
            await self._handle_login_complete_popup(page)

            return True

        except Exception as e:
            print(f"[ERROR] 인증 코드 입력 실패: {e}")
            return False

    async def _handle_login_complete_popup(self, page: Page):
        """로그인 완료 팝업 처리"""
        try:
            print("[INFO] 로그인 완료 팝업 확인 중...")

            # 로그인 완료 팝업의 확인 버튼 대기
            login_complete_button = await page.wait_for_selector(
                'button.sc-cd7f1cf7-0.sc-cd7f1cf7-1.brDrjq.gedxiE:has-text("확인")',
                timeout=10000
            )
            await login_complete_button.click()
            print("[SUCCESS] 로그인 완료 팝업 확인 버튼 클릭 완료")
            await asyncio.sleep(2)

        except Exception as popup_error:
            print(f"[INFO] 로그인 완료 팝업 처리 시도 중... ({popup_error})")
            try:
                # 더 일반적인 셀렉터 시도
                generic_confirm_button = await page.wait_for_selector(
                    'button:has-text("확인")',
                    timeout=5000
                )
                await generic_confirm_button.click()
                print("[SUCCESS] 대체 방식으로 로그인 완료 팝업 처리")
                await asyncio.sleep(2)

            except Exception as fallback_error:
                print(f"[WARNING] 로그인 완료 팝업 처리 실패: {fallback_error}")
                print("[INFO] 팝업이 없거나 이미 처리된 것으로 가정하고 계속 진행")

    async def _extract_wid_from_response(self, response, account_info: AccountInfo):
        """API 응답에서 WID 추출"""
        try:
            response_text = await response.text()
            response_json = json.loads(response_text)

            # WID 추출
            if 'wid' in response_json:
                account_info.set_wid(response_json['wid'])
                print(f"[SUCCESS] API 응답에서 WID 발견: {account_info.wid}")
            else:
                print(f"[DEBUG] API 응답에 WID 없음: {response_json}")

        except Exception as e:
            print(f"[ERROR] API 응답 파싱 실패: {e}")

    def set_timeout(self, timeout: int) -> None:
        """타임아웃 설정"""
        self.timeout = timeout
        self.wait_timeout = timeout