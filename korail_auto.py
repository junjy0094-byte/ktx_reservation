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
import requests
from datetime import datetime
from PIL import ImageGrab


# PyAutoGUI 안전 설정
pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
pyautogui.PAUSE = 0  # 동작 사이 대기 시간 없음 (최대 속도)


class KorailAutoGUI:
    """PyAutoGUI를 사용한 코레일 예약 자동화"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.last_screenshot = None

        # 대기 시간 설정 로드
        automation = self.config.get('automation', {})
        delay = automation.get('delay', {})
        self.delay_after_search = delay.get('after_search', 0.8)
        self.delay_min = delay.get('between_attempts_min', 2.0)
        self.delay_max = delay.get('between_attempts_max', 4.0)
        self.delay_screen_check = delay.get('screen_check', 0.05)

    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _save_config(self):
        """설정 파일 저장"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)

    def discord_send_message(self, text: str):
        """Discord 웹훅으로 메시지 전송"""
        try:
            notification = self.config.get('notification', {})
            discord = notification.get('discord', {})

            if not discord.get('enabled', False):
                return

            webhook_url = discord.get('webhook_url', '')
            if not webhook_url:
                return

            now = datetime.now()
            message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(text)}"}
            response = requests.post(webhook_url, data=message)
            print(f"[Discord] 메시지 전송 완료 (상태: {response.status_code})")

        except Exception as e:
            print(f"[Discord] 메시지 전송 실패: {e}")

    def save_coordinates(self, search_btn, reserve_btns, confirm_btn):
        """좌표를 설정 파일에 저장"""
        if 'automation' not in self.config:
            self.config['automation'] = {}
        if 'coordinates' not in self.config['automation']:
            self.config['automation']['coordinates'] = {}

        coords = self.config['automation']['coordinates']
        coords['search_button'] = {'x': search_btn.x, 'y': search_btn.y}
        coords['reserve_buttons'] = [{'x': pos.x, 'y': pos.y} for pos in reserve_btns]
        coords['confirm_button'] = {'x': confirm_btn.x, 'y': confirm_btn.y}

        self._save_config()
        print("[INFO] 좌표가 config.yaml에 저장되었습니다.")

    def load_coordinates(self):
        """저장된 좌표 불러오기"""
        try:
            coords = self.config.get('automation', {}).get('coordinates', {})

            search_btn = coords.get('search_button', {})
            reserve_btns = coords.get('reserve_buttons', [])
            confirm_btn = coords.get('confirm_button', {})

            # 유효성 검사
            if not search_btn or search_btn.get('x', 0) == 0:
                return None, None, None

            if not reserve_btns or len(reserve_btns) == 0:
                return None, None, None

            if not confirm_btn or confirm_btn.get('x', 0) == 0:
                return None, None, None

            # Point 객체로 변환
            from collections import namedtuple
            Point = namedtuple('Point', ['x', 'y'])

            search_pos = Point(search_btn['x'], search_btn['y'])
            reserve_positions = [Point(btn['x'], btn['y']) for btn in reserve_btns]
            confirm_pos = Point(confirm_btn['x'], confirm_btn['y'])

            return search_pos, reserve_positions, confirm_pos

        except Exception as e:
            print(f"[WARNING] 좌표 불러오기 실패: {e}")
            return None, None, None

    def has_saved_coordinates(self) -> bool:
        """저장된 좌표가 있는지 확인"""
        search, reserve, confirm = self.load_coordinates()
        return search is not None and reserve is not None and confirm is not None

    def random_delay(self, min_sec: float = None, max_sec: float = None):
        """랜덤 대기 시간"""
        min_sec = min_sec or self.delay_min
        max_sec = max_sec or self.delay_max
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    def take_screenshot(self):
        """현재 화면 스크린샷"""
        return ImageGrab.grab()

    def compare_screenshots(self, img1, img2, threshold: float = 0.95) -> bool:
        """두 스크린샷 비교"""
        if img1 is None or img2 is None:
            return False

        try:
            if img1.size != img2.size:
                return False

            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())

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
        """화면이 변경되었는지 확인"""
        time.sleep(self.delay_screen_check)
        after_screenshot = self.take_screenshot()
        is_same = self.compare_screenshots(before_screenshot, after_screenshot)
        return not is_same

    def check_reservation_success(self, before_screenshot) -> bool:
        """예매 성공 여부 확인"""
        screen_changed = self.check_screen_changed(before_screenshot)
        if screen_changed:
            print("[INFO] 화면 변화 감지됨!")
            return True
        return False

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

    def setup_coordinates(self):
        """좌표 설정 (새로 등록)"""
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

        # 3. 예매 버튼 좌표 설정
        print()
        print("3. 아무 '예약하기' 버튼을 한번 클릭해서 예매 확인 화면을 띄워주세요.")
        print("   그 다음 '예매' 또는 '결제하기' 버튼 위에 마우스를 올려놓고 Enter를 누르세요...")
        input()
        confirm_btn_pos = pyautogui.position()
        print(f"   -> 예매 버튼 좌표: ({confirm_btn_pos.x}, {confirm_btn_pos.y})")

        # 좌표 저장
        self.save_coordinates(search_btn_pos, reserve_btn_positions, confirm_btn_pos)

        return search_btn_pos, reserve_btn_positions, confirm_btn_pos

    def print_coordinates_info(self, search_btn_pos, reserve_btn_positions, confirm_btn_pos):
        """좌표 정보 출력"""
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

    def print_delay_info(self):
        """대기 시간 설정 출력"""
        print(f"[INFO] 대기 시간 설정 (config.yaml에서 변경 가능)")
        print(f"  - 조회 후 대기: {self.delay_after_search}초")
        print(f"  - 재시도 간격: {self.delay_min}~{self.delay_max}초 (랜덤)")
        print(f"  - 화면 확인: {self.delay_screen_check}초")

    def run_reservation_loop(self, search_btn_pos, reserve_btn_positions, confirm_btn_pos):
        """예약 루프 실행"""
        max_attempts = self.config['reservation']['max_attempts']

        print(f"[INFO] 최대 시도 횟수: {max_attempts}회")
        print(f"[INFO] 등록된 열차: {len(reserve_btn_positions)}개 (순서대로 시도)")
        self.print_delay_info()
        print()
        print("[ 동작 순서 ]")
        print("1. 조회하기 클릭")
        print("2. 각 열차별 예약하기 → 예매 버튼 순서대로 시도")
        print("3. 화면 변화 확인 → 성공 시 종료, 실패 시 다음 열차 시도")
        print("4. 모든 열차 실패 시 새로고침 후 반복")
        print()
        input("자동 예약을 시작하려면 Enter를 누르세요...")
        print()

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
                time.sleep(self.delay_after_search)
                print("완료")

                # Step 2: 각 열차별로 예약 시도 (최대 속도)
                for train_idx, reserve_btn_pos in enumerate(reserve_btn_positions, 1):
                    self.fast_click(reserve_btn_pos.x, reserve_btn_pos.y)
                    before_confirm = self.take_screenshot()
                    self.fast_click(confirm_btn_pos.x, confirm_btn_pos.y)

                    if self.check_reservation_success(before_confirm):
                        print(f"\n  [!] {train_idx}번 열차 - 화면 변화 감지!")
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

                            # 소리 알림
                            if self.config.get('notification', {}).get('sound', False):
                                for _ in range(5):
                                    print('\a', end='', flush=True)
                                    time.sleep(0.3)

                            # Discord 알림
                            self.discord_send_message(
                                f"🎉 KTX 예매 성공! {train_idx}번 열차 예매가 완료되었습니다. 결제를 진행해주세요!"
                            )
                            break
                        else:
                            print(f"[INFO] {train_idx}번 열차 실패, 다음 열차 시도...")

                if not reservation_success:
                    print(f"  -> {len(reserve_btn_positions)}개 열차 모두 클릭 완료 (좌석 없음)")

                if reservation_success:
                    break

                delay = self.random_delay()
                print(f"  [대기] 모든 열차 실패. {delay:.1f}초 후 재시도...")

            except pyautogui.FailSafeException:
                print("\n[중단] 안전장치 작동 - 마우스가 화면 모서리로 이동됨")
                break
            except KeyboardInterrupt:
                print("\n[중단] 사용자 중단 (Ctrl+C)")
                break
            except Exception as e:
                print(f"\n[오류] {e}")
                self.random_delay()

        if not reservation_success:
            print("\n[INFO] 자동 예약 종료 (성공하지 못함)")

        print("\n프로그램을 종료합니다.")

    def run_with_coordinates(self):
        """좌표 기반 자동화 실행"""
        self.wait_for_user_setup()

        # 저장된 좌표 확인
        if self.has_saved_coordinates():
            print("\n[ 저장된 좌표 발견 ]")
            search, reserve, confirm = self.load_coordinates()
            print(f"  조회하기: ({search.x}, {search.y})")
            print(f"  예약하기: {len(reserve)}개")
            for i, pos in enumerate(reserve, 1):
                print(f"    - {i}번 열차: ({pos.x}, {pos.y})")
            print(f"  예매: ({confirm.x}, {confirm.y})")
            print()
            choice = input("저장된 좌표를 사용할까요? (y: 사용 / n: 새로 설정): ").strip().lower()

            if choice == 'y':
                search_btn_pos, reserve_btn_positions, confirm_btn_pos = search, reserve, confirm
            else:
                search_btn_pos, reserve_btn_positions, confirm_btn_pos = self.setup_coordinates()
        else:
            search_btn_pos, reserve_btn_positions, confirm_btn_pos = self.setup_coordinates()

        self.print_coordinates_info(search_btn_pos, reserve_btn_positions, confirm_btn_pos)
        self.run_reservation_loop(search_btn_pos, reserve_btn_positions, confirm_btn_pos)

    def run_simple_refresh(self):
        """단순 새로고침 모드"""
        self.wait_for_user_setup()

        print("\n[ 단순 새로고침 모드 ]")
        print("이 모드는 F5 키를 눌러 페이지를 새로고침합니다.")
        print("예약 가능한 좌석이 보이면 직접 클릭하세요!")
        print()

        max_attempts = self.config['reservation']['max_attempts']
        self.print_delay_info()
        print()
        input("시작하려면 Enter를 누르세요...")
        print()

        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            current_time = datetime.now().strftime('%H:%M:%S')

            try:
                pyautogui.press('f5')
                delay = self.random_delay()
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
        print("\n" + "=" * 60)
        print("  실행 모드를 선택하세요")
        print("=" * 60)
        print("1. 좌표 기반 자동 클릭 (추천)")
        print("2. 좌표 새로 설정하기")
        print("3. 단순 새로고침 모드")
        print()

        if self.has_saved_coordinates():
            print("[INFO] 저장된 좌표가 있습니다. (1번 선택 시 사용 가능)")
        else:
            print("[INFO] 저장된 좌표가 없습니다. (새로 설정 필요)")

        print()
        choice = input("선택 (1/2/3): ").strip()

        if choice == "1":
            self.run_with_coordinates()
        elif choice == "2":
            self.wait_for_user_setup()
            search_btn_pos, reserve_btn_positions, confirm_btn_pos = self.setup_coordinates()
            self.print_coordinates_info(search_btn_pos, reserve_btn_positions, confirm_btn_pos)
            self.run_reservation_loop(search_btn_pos, reserve_btn_positions, confirm_btn_pos)
        else:
            self.run_simple_refresh()


if __name__ == "__main__":
    auto = KorailAutoGUI()
    auto.run()
