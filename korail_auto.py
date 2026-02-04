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
import random
import yaml
import pyautogui
import pyperclip
import subprocess
import platform
from datetime import datetime
from PIL import ImageGrab


# PyAutoGUI 안전 설정
pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
pyautogui.PAUSE = 0  # 동작 사이 대기 시간 없음 (최대 속도)


class KorailAutoGUI:
    """PyAutoGUI를 사용한 코레일 예약 자동화"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.last_screenshot = None

    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def random_delay(self, min_sec: float = 2.0, max_sec: float = 4.0):
        """랜덤 대기 시간"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    def take_screenshot(self):
        """현재 화면 스크린샷"""
        return ImageGrab.grab()

    def compare_screenshots(self, img1, img2, threshold: float = 0.95) -> bool:
        """
        두 스크린샷 비교

        Returns:
            bool: True면 화면이 거의 동일 (변화 없음), False면 화면이 변경됨
        """
        if img1 is None or img2 is None:
            return False

        try:
            # 이미지 크기가 다르면 다른 것으로 판단
            if img1.size != img2.size:
                return False

            # 픽셀 비교 (샘플링)
            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())

            # 샘플링으로 빠르게 비교
            sample_size = min(10000, len(pixels1))
            sample_indices = random.sample(range(len(pixels1)), sample_size)

            matches = 0
            for idx in sample_indices:
                if pixels1[idx] == pixels2[idx]:
                    matches += 1

            similarity = matches / sample_size
            return similarity >= threshold

        except Exception:
            return False

    def check_screen_changed(self, before_screenshot) -> bool:
        """
        화면이 변경되었는지 확인

        Args:
            before_screenshot: 이전 스크린샷

        Returns:
            bool: True면 화면이 변경됨 (예매 페이지로 이동 등)
        """
        time.sleep(0.05)  # 최소 대기 (50ms)
        after_screenshot = self.take_screenshot()

        # 화면이 동일하면 False, 다르면 True
        is_same = self.compare_screenshots(before_screenshot, after_screenshot)
        return not is_same

    def check_reservation_success(self, before_screenshot) -> bool:
        """
        예매 성공 여부 확인

        Args:
            before_screenshot: 예매 버튼 클릭 전 스크린샷

        Returns:
            bool: 예매 성공 여부
        """
        # 방법 1: 화면 변화 감지
        screen_changed = self.check_screen_changed(before_screenshot)

        if screen_changed:
            print("[INFO] 화면 변화 감지됨!")
            return True

        return False

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

    def fast_click(self, x: int, y: int):
        """빠른 클릭 (최소 대기)"""
        pyautogui.click(x, y)

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

    def run_with_coordinates(self):
        """좌표 기반 자동화 실행 (사용자가 좌표 설정)"""
        self.wait_for_user_setup()

        print("\n[ 좌표 설정 ]")
        print("각 버튼의 좌표를 설정합니다.")
        print()

        # 1. 조회하기 버튼 좌표 설정
        print("1. '조회하기' 버튼 위에 마우스를 올려놓고 Enter를 누르세요...")
        input()
        search_btn_pos = pyautogui.position()
        print(f"   -> 조회하기 버튼 좌표: ({search_btn_pos.x}, {search_btn_pos.y})")

        # 2. 예약하기 버튼 좌표 설정 (여러 개 가능)
        print()
        print("2. 예약하기 버튼을 설정합니다. (여러 열차 시간대 선택 가능)")
        print("   원하는 열차들의 '예약하기' 버튼을 순서대로 등록합니다.")
        print()

        reserve_btn_positions = []
        train_num = 1

        while True:
            print(f"   [{train_num}번째 열차] 예약하기 버튼 위에 마우스를 올려놓고 Enter")
            print(f"   (등록 완료하려면 'q' 입력 후 Enter): ", end="")
            user_input = input().strip().lower()

            if user_input == 'q':
                if len(reserve_btn_positions) == 0:
                    print("   [경고] 최소 1개의 예약하기 버튼을 등록해야 합니다!")
                    continue
                break

            pos = pyautogui.position()
            reserve_btn_positions.append(pos)
            print(f"   -> {train_num}번 열차 예약하기 버튼: ({pos.x}, {pos.y})")
            train_num += 1

        print(f"\n   총 {len(reserve_btn_positions)}개의 열차 등록 완료!")

        # 3. 예매 버튼 좌표 설정 (예약하기 클릭 후 나오는 팝업/페이지의 예매 버튼)
        print()
        print("3. 아무 '예약하기' 버튼을 한번 클릭해서 예매 확인 화면을 띄워주세요.")
        print("   그 다음 '예매' 또는 '결제하기' 버튼 위에 마우스를 올려놓고 Enter를 누르세요...")
        input()
        confirm_btn_pos = pyautogui.position()
        print(f"   -> 예매 버튼 좌표: ({confirm_btn_pos.x}, {confirm_btn_pos.y})")

        print()
        print("=" * 60)
        print("  좌표 설정 완료!")
        print(f"  조회하기 버튼: ({search_btn_pos.x}, {search_btn_pos.y})")
        print(f"  예약하기 버튼: {len(reserve_btn_positions)}개 등록")
        for i, pos in enumerate(reserve_btn_positions, 1):
            print(f"    - {i}번 열차: ({pos.x}, {pos.y})")
        print(f"  예매 버튼:     ({confirm_btn_pos.x}, {confirm_btn_pos.y})")
        print("=" * 60)
        print()

        # 예약 설정
        max_attempts = self.config['reservation']['max_attempts']

        print(f"[INFO] 최대 시도 횟수: {max_attempts}회")
        print(f"[INFO] 새로고침 간격: 2~4초 (랜덤)")
        print(f"[INFO] 등록된 열차: {len(reserve_btn_positions)}개 (순서대로 시도)")
        print()
        print("[ 동작 순서 ]")
        print("1. 조회하기 클릭")
        print("2. 각 열차별 예약하기 → 예매 버튼 순서대로 시도")
        print("3. 화면 변화 확인 → 성공 시 종료, 실패 시 다음 열차 시도")
        print("4. 모든 열차 실패 시 새로고침 후 반복")
        print()
        input("자동 예약을 시작하려면 Enter를 누르세요...")
        print()

        # 자동 예약 루프
        attempt = 0
        reservation_success = False

        while attempt < max_attempts and not reservation_success:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"\n[{current_time}] === 시도 {attempt}/{max_attempts} ===")

            try:
                # Step 1: 조회하기 버튼 클릭
                print("  [1] 조회하기 클릭...", end=" ", flush=True)
                self.fast_click(search_btn_pos.x, search_btn_pos.y)
                time.sleep(0.8)  # 조회 결과 로딩 최소 대기
                print("완료")

                # Step 2: 각 열차별로 예약 시도 (최대 속도)
                for train_idx, reserve_btn_pos in enumerate(reserve_btn_positions, 1):
                    # 예약하기 버튼 즉시 클릭
                    self.fast_click(reserve_btn_pos.x, reserve_btn_pos.y)

                    # 예매 버튼 즉시 클릭 (대기 없음)
                    before_confirm = self.take_screenshot()
                    self.fast_click(confirm_btn_pos.x, confirm_btn_pos.y)

                    # 예매 성공 확인
                    if self.check_reservation_success(before_confirm):
                        print(f"\n  [!] {train_idx}번 열차 - 화면 변화 감지!")

                        # 추가 확인: 사용자에게 물어봄
                        print()
                        print("=" * 60)
                        print(f"  [확인] {train_idx}번 열차 예매가 성공한 것 같습니다!")
                        print("  화면을 확인해주세요.")
                        print("=" * 60)

                        response = input("예매 성공했나요? (y/n): ").strip().lower()
                        if response == 'y':
                            reservation_success = True
                            print()
                            print("*" * 60)
                            print(f"  축하합니다! {train_idx}번 열차 예매 성공!")
                            print("  결제를 진행해주세요.")
                            print("*" * 60)

                            # 알림음
                            if self.config.get('notification', {}).get('sound', False):
                                for _ in range(5):
                                    print('\a', end='', flush=True)
                                    time.sleep(0.3)
                            break
                        else:
                            print(f"[INFO] {train_idx}번 열차 실패, 다음 열차 시도...")

                # 시도 결과 출력 (한 줄로)
                if not reservation_success:
                    print(f"  -> {len(reserve_btn_positions)}개 열차 모두 클릭 완료 (좌석 없음)")

                # 예약 성공했으면 루프 종료
                if reservation_success:
                    break

                # 모든 열차 실패 시 랜덤 대기 후 재시도
                delay = self.random_delay(2.0, 4.0)
                print(f"  [대기] 모든 열차 실패. {delay:.1f}초 후 재시도...")

            except pyautogui.FailSafeException:
                print("\n[중단] 안전장치 작동 - 마우스가 화면 모서리로 이동됨")
                break
            except KeyboardInterrupt:
                print("\n[중단] 사용자 중단 (Ctrl+C)")
                break
            except Exception as e:
                print(f"\n[오류] {e}")
                self.random_delay(2.0, 4.0)

        if not reservation_success:
            print("\n[INFO] 자동 예약 종료 (성공하지 못함)")

        print("\n프로그램을 종료합니다.")

    def run_simple_refresh(self):
        """단순 새로고침 모드 (가장 간단한 방식)"""
        self.wait_for_user_setup()

        print("\n[ 단순 새로고침 모드 ]")
        print("이 모드는 F5 키를 눌러 페이지를 새로고침합니다.")
        print("예약 가능한 좌석이 보이면 직접 클릭하세요!")
        print()

        max_attempts = self.config['reservation']['max_attempts']

        print(f"새로고침 간격: 2~4초 (랜덤)")
        print()
        input("시작하려면 Enter를 누르세요...")
        print()

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')

            try:
                pyautogui.press('f5')
                delay = self.random_delay(2.0, 4.0)
                print(f"[{current_time}] 새로고침 {attempt}/{max_attempts} (다음까지 {delay:.1f}초)")

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
