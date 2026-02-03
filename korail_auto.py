"""
코레일 KTX 취소표 자동 예약 프로그램
PyAutoGUI를 사용한 OS 레벨 자동화 (자동화 감지 완전 우회)

사용법:
1. Chrome을 직접 열고 https://www.korail.com 접속
2. 로그인 완료
3. 승차권 예매 페이지로 이동
4. 이 스크립트 실행: python korail_auto.py
"""

import time
import yaml
import pyautogui
import pyperclip
import subprocess
import platform
from datetime import datetime


# PyAutoGUI 안전 설정
pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
pyautogui.PAUSE = 0.5  # 각 동작 사이 대기 시간


class KorailAutoGUI:
    """PyAutoGUI를 사용한 코레일 예약 자동화"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def open_korail_website(self):
        """코레일 웹사이트 열기"""
        url = "https://www.korail.com/ticket/main/mainForm.do"

        if platform.system() == "Windows":
            subprocess.Popen(['start', url], shell=True)
        elif platform.system() == "Darwin":
            subprocess.Popen(['open', url])
        else:
            subprocess.Popen(['xdg-open', url])

        print("[INFO] 브라우저가 열렸습니다. 10초 대기...")
        time.sleep(10)

    def type_korean(self, text: str):
        """한글 입력 (클립보드 사용)"""
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.3)

    def find_and_click(self, image_path: str, confidence: float = 0.8, timeout: int = 10) -> bool:
        """
        화면에서 이미지를 찾아 클릭

        Args:
            image_path: 찾을 이미지 파일 경로
            confidence: 매칭 정확도 (0-1)
            timeout: 최대 대기 시간 (초)

        Returns:
            bool: 성공 여부
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                if location:
                    center = pyautogui.center(location)
                    pyautogui.click(center)
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def click_at_position(self, x: int, y: int):
        """특정 좌표 클릭"""
        pyautogui.click(x, y)
        time.sleep(0.3)

    def refresh_page(self):
        """페이지 새로고침 (F5)"""
        pyautogui.press('f5')
        time.sleep(2)

    def scroll_down(self, clicks: int = 3):
        """페이지 스크롤"""
        pyautogui.scroll(-clicks)
        time.sleep(0.5)

    def wait_for_user_setup(self):
        """사용자가 브라우저 설정을 완료할 때까지 대기"""
        print("\n" + "=" * 60)
        print("  코레일 취소표 자동 예약 프로그램 (PyAutoGUI)")
        print("=" * 60)
        print()
        print("[ 사전 준비 사항 ]")
        print("1. Chrome 브라우저를 직접 열어주세요")
        print("2. https://www.korail.com 에 접속하세요")
        print("3. 코레일 멤버십으로 로그인하세요")
        print("4. '승차권 예매' 메뉴로 이동하세요")
        print("5. 출발역, 도착역, 날짜, 시간을 입력하세요")
        print("6. '조회하기' 버튼을 눌러 열차 목록을 표시하세요")
        print()
        print("[ 주의 사항 ]")
        print("- 프로그램 실행 중 마우스를 화면 왼쪽 상단 모서리로")
        print("  이동하면 프로그램이 즉시 중단됩니다 (안전장치)")
        print("- 브라우저 창이 항상 보이도록 해주세요")
        print()

        input("준비가 완료되면 Enter를 눌러주세요...")
        print()

    def check_seat_availability_manual(self) -> bool:
        """
        사용자에게 좌석 상태 확인 요청

        Returns:
            bool: 예약 가능 여부
        """
        print("\n[확인] 현재 화면에서 예약 가능한 좌석이 있나요?")
        response = input("예약 가능하면 'y', 없으면 'n' 입력: ").strip().lower()
        return response == 'y'

    def run_with_coordinates(self):
        """좌표 기반 자동화 실행 (사용자가 좌표 설정)"""
        self.wait_for_user_setup()

        print("\n[ 좌표 설정 ]")
        print("예약하기 버튼의 좌표를 설정해야 합니다.")
        print()

        # 조회하기 버튼 좌표 설정
        print("1. '조회하기' 버튼 위에 마우스를 올려놓고 Enter를 누르세요...")
        input()
        search_btn_pos = pyautogui.position()
        print(f"   -> 조회하기 버튼 좌표: {search_btn_pos}")

        print()
        print("2. 첫 번째 열차의 '예약하기' 버튼(일반실) 위에 마우스를 올려놓고 Enter를 누르세요...")
        input()
        reserve_btn_pos = pyautogui.position()
        print(f"   -> 예약하기 버튼 좌표: {reserve_btn_pos}")

        print()
        print("=" * 60)
        print(f"  설정 완료!")
        print(f"  조회하기 버튼: ({search_btn_pos.x}, {search_btn_pos.y})")
        print(f"  예약하기 버튼: ({reserve_btn_pos.x}, {reserve_btn_pos.y})")
        print("=" * 60)
        print()

        # 예약 설정
        refresh_interval = self.config['reservation']['refresh_interval']
        max_attempts = self.config['reservation']['max_attempts']

        print(f"[INFO] 새로고침 간격: {refresh_interval}초")
        print(f"[INFO] 최대 시도 횟수: {max_attempts}회")
        print()
        input("자동 예약을 시작하려면 Enter를 누르세요...")
        print()

        # 자동 예약 루프
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}] 시도 {attempt}/{max_attempts}", end=" - ")

            try:
                # 예약하기 버튼 클릭 시도
                pyautogui.click(reserve_btn_pos.x, reserve_btn_pos.y)
                time.sleep(1)

                # 화면 변화 확인 (간단한 방법: 사용자에게 확인)
                # 실제로는 화면 캡처 후 비교하는 방식 사용 가능

                print("클릭 완료")

                # 새로고침 (조회하기 버튼 클릭)
                time.sleep(refresh_interval)
                pyautogui.click(search_btn_pos.x, search_btn_pos.y)
                time.sleep(2)

            except pyautogui.FailSafeException:
                print("\n[중단] 안전장치 작동 - 마우스가 화면 모서리로 이동됨")
                break
            except Exception as e:
                print(f"오류: {e}")
                time.sleep(refresh_interval)

        print("\n[INFO] 자동 예약 종료")

    def run_simple_refresh(self):
        """단순 새로고침 모드 (가장 간단한 방식)"""
        self.wait_for_user_setup()

        print("\n[ 단순 새로고침 모드 ]")
        print("이 모드는 F5 키를 눌러 페이지를 새로고침합니다.")
        print("예약 가능한 좌석이 보이면 직접 클릭하세요!")
        print()

        refresh_interval = self.config['reservation']['refresh_interval']
        max_attempts = self.config['reservation']['max_attempts']

        print(f"새로고침 간격: {refresh_interval}초")
        print()
        input("시작하려면 Enter를 누르세요...")
        print()

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}] 새로고침 {attempt}/{max_attempts}")

            try:
                pyautogui.press('f5')
                time.sleep(refresh_interval)

            except pyautogui.FailSafeException:
                print("\n[중단] 안전장치 작동")
                break
            except KeyboardInterrupt:
                print("\n[중단] 사용자 중단 (Ctrl+C)")
                break

        print("\n[INFO] 종료")

    def run(self):
        """메인 실행"""
        print("\n실행 모드를 선택하세요:")
        print("1. 좌표 기반 자동 클릭 (추천)")
        print("2. 단순 새로고침 모드")
        print()

        choice = input("선택 (1 또는 2): ").strip()

        if choice == "1":
            self.run_with_coordinates()
        else:
            self.run_simple_refresh()


if __name__ == "__main__":
    auto = KorailAutoGUI()
    auto.run()
