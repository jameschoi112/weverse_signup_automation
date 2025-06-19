"""
이메일 생성 서비스
"""
import random
import string
import time
from typing import Set, List
from config.settings import EMAIL_SETTINGS


class EmailGenerator:
    """이메일 생성기"""

    def __init__(self):
        self.used_emails: Set[str] = set()

    def generate_email(self, environment: str, base_email: str = None) -> str:
        """
        환경에 따른 이메일 생성

        Args:
            environment: "qa" 또는 "real"
            base_email: Real 환경용 기본 이메일

        Returns:
            생성된 이메일 주소
        """
        if environment == "qa":
            return self._generate_qa_email()
        elif environment == "real":
            if not base_email:
                raise ValueError("Real 환경에서는 base_email이 필요합니다")
            return self._generate_dot_email(base_email)
        else:
            raise ValueError(f"지원하지 않는 환경: {environment}")

    def _generate_qa_email(self) -> str:
        """QA 환경용 이메일 생성"""
        random_prefix = self._generate_random_string(8)
        email = f"{random_prefix}{EMAIL_SETTINGS['qa_domain']}"

        # 중복 체크
        while email in self.used_emails:
            random_prefix = self._generate_random_string(8)
            email = f"{random_prefix}{EMAIL_SETTINGS['qa_domain']}"

        self.used_emails.add(email)
        return email

    def _generate_dot_email(self, base_email: str) -> str:
        """Gmail의 점 무시 특성을 이용한 이메일 생성"""
        if EMAIL_SETTINGS['gmail_domain'] not in base_email.lower():
            raise ValueError("Gmail 주소가 아닙니다")

        username, domain = base_email.split('@')

        attempts = 0
        max_attempts = 100

        while attempts < max_attempts:
            # 복잡도를 점진적으로 증가
            if attempts < 20:
                email = self._generate_simple_dots(username, domain)
            elif attempts < 50:
                email = self._generate_complex_dots(username, domain)
            elif attempts < 80:
                email = self._generate_maximum_dots(username, domain)
            else:
                email = self._generate_systematic_dots(username, domain, attempts - 80)

            if email not in self.used_emails:
                self.used_emails.add(email)
                return email

            attempts += 1

        # 최후의 수단: 타임스탬프 + 랜덤 추가
        timestamp = str(int(time.time() * 1000))[-6:]
        random_suffix = self._generate_random_string(3)
        fallback_email = f"{username}.{timestamp}.{random_suffix}@{domain}"
        self.used_emails.add(fallback_email)
        return fallback_email

    def _generate_simple_dots(self, username: str, domain: str) -> str:
        """기본 dot 패턴 (2-3개)"""
        chars = list(username)
        username_len = len(chars)

        if username_len < 3:
            timestamp = str(int(time.time() * 1000))[-4:]
            return f"{username}.{timestamp}@{domain}"

        max_dots = min(3, username_len - 1)
        dot_count = random.randint(2, max_dots)
        available_positions = list(range(1, username_len))
        dot_positions = random.sample(available_positions, dot_count)

        for pos in sorted(dot_positions, reverse=True):
            chars.insert(pos, '.')

        return f"{''.join(chars)}@{domain}"

    def _generate_complex_dots(self, username: str, domain: str) -> str:
        """복잡한 dot 패턴"""
        chars = list(username)
        username_len = len(chars)

        if username_len < 4:
            new_chars = []
            for i, char in enumerate(chars):
                new_chars.append(char)
                if i < len(chars) - 1:
                    new_chars.append('.')
            return f"{''.join(new_chars)}@{domain}"

        max_dots = min(username_len // 2, username_len - 1)
        dot_count = random.randint(max_dots // 2, max_dots)
        available_positions = list(range(1, username_len))
        dot_positions = random.sample(available_positions, dot_count)

        for pos in sorted(dot_positions, reverse=True):
            chars.insert(pos, '.')

        return f"{''.join(chars)}@{domain}"

    def _generate_maximum_dots(self, username: str, domain: str) -> str:
        """최대한 많은 dot 사용"""
        chars = list(username)
        patterns = [
            self._pattern_every_two_chars,
            self._pattern_alternating,
            self._pattern_front_heavy,
            self._pattern_back_heavy,
            self._pattern_middle_heavy
        ]
        pattern_func = random.choice(patterns)
        new_username = pattern_func(chars)
        return f"{new_username}@{domain}"

    def _generate_systematic_dots(self, username: str, domain: str, sequence: int) -> str:
        """체계적인 dot 패턴"""
        chars = list(username)
        username_len = len(chars)
        binary = format(sequence, f'0{username_len - 1}b')
        result_chars = [chars[0]]

        for i, bit in enumerate(binary):
            if bit == '1' and i + 1 < username_len:
                result_chars.append('.')
            if i + 1 < username_len:
                result_chars.append(chars[i + 1])

        return f"{''.join(result_chars)}@{domain}"

    def _pattern_every_two_chars(self, chars: List[str]) -> str:
        """2글자마다 dot"""
        result = []
        for i, char in enumerate(chars):
            result.append(char)
            if (i + 1) % 2 == 0 and i < len(chars) - 1:
                result.append('.')
        return ''.join(result)

    def _pattern_alternating(self, chars: List[str]) -> str:
        """번갈아가며 dot"""
        result = []
        for i, char in enumerate(chars):
            result.append(char)
            if i % 2 == 0 and i < len(chars) - 1:
                result.append('.')
        return ''.join(result)

    def _pattern_front_heavy(self, chars: List[str]) -> str:
        """앞쪽에 많은 dot"""
        result = [chars[0]]
        middle = len(chars) // 2
        for i in range(1, len(chars)):
            if i <= middle:
                result.append('.')
            result.append(chars[i])
        return ''.join(result)

    def _pattern_back_heavy(self, chars: List[str]) -> str:
        """뒤쪽에 많은 dot"""
        result = [chars[0]]
        middle = len(chars) // 2
        for i in range(1, len(chars)):
            if i > middle:
                result.append('.')
            result.append(chars[i])
        return ''.join(result)

    def _pattern_middle_heavy(self, chars: List[str]) -> str:
        """중간에 많은 dot"""
        result = []
        length = len(chars)
        start = length // 3
        end = 2 * length // 3
        for i, char in enumerate(chars):
            result.append(char)
            if start <= i < end and i < len(chars) - 1:
                result.append('.')
        return ''.join(result)

    def _generate_random_string(self, length: int = 8) -> str:
        """랜덤 문자열 생성"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def clear_used_emails(self) -> None:
        """사용된 이메일 목록 초기화"""
        self.used_emails.clear()

    def get_used_emails_count(self) -> int:
        """사용된 이메일 개수 반환"""
        return len(self.used_emails)