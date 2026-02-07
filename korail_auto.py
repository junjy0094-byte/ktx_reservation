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
import io
from datetime import datetime
from PIL import ImageGrab


# PyAutoGUI 안전 설정
pyautogui.FAILSAFE = True  # 마우스를 화면 모서리로 이동하면 중단
pyautogui.PAUSE = 0  # 동작 사이 대기 시간 없음 (최대 속도)


class KorailAutoGUI:
    """PyAutoGUI를 사용한 코레일 예약 자동화"""

    def __init__(self, config_path: str = "config.yaml", debug: bool = False):
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.last_screenshot = None
        self.baseline_screenshot = None  # 기준 스크린샷 (최초 1회만 저장)
        self.debug = debug  # 디버깅 모드
        self.debug_count = 0  # 디버깅 스크린샷 카운터

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

    def discord_send_message(self, text: str, image_path: str = None):
        """Discord 웹훅으로 메시지 전송 (이미지 첨부 가능)"""
        try:
            notification = self.config.get('notification', {})
            discord = notification.get('discord', {})

            if not discord.get('enabled', False):
                print("[Discord] 알림이 비활성화되어 있습니다. (notification.discord.enabled = false)")
                return

            webhook_url = discord.get('webhook_url', '')
            if not webhook_url:
                print("[Discord] 웹훅 URL이 설정되지 않았습니다. (notification.discord.webhook_url)")
                return

            now = datetime.now()
            content = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(text)}"

            if image_path:
                # 이미지와 함께 전송
                with open(image_path, 'rb') as f:
                    files = {'file': (image_path, f, 'image/png')}
                    data = {'content': content}
                    response = requests.post(webhook_url, data=data, files=files, timeout=30)
            else:
                # 텍스트만 전송
                message = {"content": content}
                response = requests.post(webhook_url, json=message, timeout=10)

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

    def get_pixel_color(self, x: int, y: int) -> tuple:
        """특정 좌표의 픽셀 색상 가져오기 (RGB)"""
        img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1))
        return img.getpixel((0, 0))[:3]

    def is_color_white(self, color: tuple, threshold: int = 30) -> bool:
        """색상이 흰색인지 확인 (RGB 각각 225 이상)"""
        return color[0] >= (255 - threshold) and color[1] >= (255 - threshold) and color[2] >= (255 - threshold)

    def is_color_similar(self, color1: tuple, color2: tuple, threshold: int = 30) -> bool:
        """두 색상이 비슷한지 확인"""
        diff = abs(color1[0] - color2[0]) + abs(color1[1] - color2[1]) + abs(color1[2] - color2[2])
        return diff <= threshold

    def load_detection_config(self):
        """로딩 감지 좌표 및 색상 설정 불러오기"""
        try:
            detection = self.config.get('automation', {}).get('detection', {})
            coord1 = detection.get('coord1', {})
            coord2 = detection.get('coord2', {})
            coord3 = detection.get('coord3', {})
            gray_color = detection.get('gray_color', {'r': 128, 'g': 128, 'b': 128})
            success_color = detection.get('success_color', {'r': 0, 'g': 0, 'b': 0})

            from collections import namedtuple
            Point = namedtuple('Point', ['x', 'y'])

            if coord1.get('x', 0) == 0 or coord2.get('x', 0) == 0 or coord3.get('x', 0) == 0:
                return None, None, None, None, None

            return (
                Point(coord1['x'], coord1['y']),
                Point(coord2['x'], coord2['y']),
                Point(coord3['x'], coord3['y']),
                (gray_color['r'], gray_color['g'], gray_color['b']),
                (success_color['r'], success_color['g'], success_color['b'])
            )
        except:
            return None, None, None, None, None

    def save_detection_config(self, coord1, coord2, coord3, gray_color, success_color):
        """로딩 감지 좌표 및 색상 설정 저장"""
        if 'automation' not in self.config:
            self.config['automation'] = {}
        if 'detection' not in self.config['automation']:
            self.config['automation']['detection'] = {}

        detection = self.config['automation']['detection']
        detection['coord1'] = {'x': coord1.x, 'y': coord1.y}
        detection['coord2'] = {'x': coord2.x, 'y': coord2.y}
        detection['coord3'] = {'x': coord3.x, 'y': coord3.y}
        detection['gray_color'] = {'r': gray_color[0], 'g': gray_color[1], 'b': gray_color[2]}
        detection['success_color'] = {'r': success_color[0], 'g': success_color[1], 'b': success_color[2]}

        self._save_config()
        print("[INFO] 로딩 감지 설정이 config.yaml에 저장되었습니다.")

    def wait_for_loading_complete(self, coord1, coord2, gray_color, timeout: float = 10.0) -> bool:
        """
        로딩 완료 대기
        - 로딩 중: coord1=흰색 AND coord2=회색 아님
        - 로딩 완료: coord1=흰색 아님 AND coord2=흰색
        """
        start_time = time.time()
        check_count = 0

        while time.time() - start_time < timeout:
            color1 = self.get_pixel_color(coord1.x, coord1.y)
            color2 = self.get_pixel_color(coord2.x, coord2.y)

            is_coord1_white = self.is_color_white(color1)
            is_coord2_white = self.is_color_white(color2)
            is_coord2_gray = self.is_color_similar(color2, gray_color, threshold=40)

            if self.debug:
                check_count += 1
                if check_count % 10 == 0:  # 10번에 한 번만 출력
                    print(f"[DEBUG] coord1={color1} (white:{is_coord1_white}), coord2={color2} (white:{is_coord2_white}, gray:{is_coord2_gray})")

            # 로딩 완료 조건: coord1이 흰색 아님 AND coord2가 흰색
            if not is_coord1_white and is_coord2_white:
                if self.debug:
                    print(f"[DEBUG] 로딩 완료! coord1={color1}, coord2={color2}")
                return True

            time.sleep(0.05)  # 50ms 간격으로 확인

        print("[WARNING] 로딩 타임아웃")
        return False

    def check_reservation_success_by_color(self, coord1, coord2, coord3, gray_color, success_color) -> bool:
        """
        예매 성공 여부 확인 (색상 기반)
        - 로딩 중: coord1=흰색 AND coord2=회색 아님
        - 로딩 완료: coord1=흰색 아님 AND coord2=흰색
        - 성공: coord3=특정색
        """
        color1 = self.get_pixel_color(coord1.x, coord1.y)
        color2 = self.get_pixel_color(coord2.x, coord2.y)

        is_coord1_white = self.is_color_white(color1)
        is_coord2_white = self.is_color_white(color2)
        is_coord2_gray = self.is_color_similar(color2, gray_color, threshold=40)

        if self.debug:
            print(f"[DEBUG] 확인 - coord1={color1} (white:{is_coord1_white}), coord2={color2} (white:{is_coord2_white}, gray:{is_coord2_gray})")

        # 로딩 중 상태인지 확인: coord1=흰색 AND coord2=회색 아님
        if is_coord1_white and not is_coord2_gray:
            # 로딩 완료까지 대기
            if self.wait_for_loading_complete(coord1, coord2, gray_color):
                # 로딩 완료 후 coord3 색상 확인
                color3 = self.get_pixel_color(coord3.x, coord3.y)
                is_success = self.is_color_similar(color3, success_color, threshold=40)
                if self.debug:
                    print(f"[DEBUG] coord3={color3}, success_color={success_color}, is_success={is_success}")
                return is_success
            return False

        # 이미 로딩 완료 상태
        if not is_coord1_white and is_coord2_white:
            # coord3 색상 확인
            color3 = self.get_pixel_color(coord3.x, coord3.y)
            is_success = self.is_color_similar(color3, success_color, threshold=40)
            if self.debug:
                print(f"[DEBUG] coord3={color3}, success_color={success_color}, is_success={is_success}")
            return is_success

        return False

    def random_delay(self, min_sec: float = None, max_sec: float = None):
        """랜덤 대기 시간"""
        min_sec = min_sec or self.delay_min
        max_sec = max_sec or self.delay_max
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay

    def take_screenshot(self, region=None):
        """
        현재 화면 스크린샷

        Args:
            region: (left, top, right, bottom) 특정 영역만 캡처
        """
        if region:
            return ImageGrab.grab(bbox=region)
        return ImageGrab.grab()

    def take_screenshot_around(self, x: int, y: int, size: int = 300):
        """
        특정 좌표 주변 영역 스크린샷

        Args:
            x, y: 중심 좌표
            size: 캡처 영역 크기 (정사각형)
        """
        half = size // 2
        # 화면 범위 내로 조정
        screen_width, screen_height = pyautogui.size()
        left = max(0, x - half)
        top = max(0, y - half)
        right = min(screen_width, x + half)
        bottom = min(screen_height, y + half)
        return ImageGrab.grab(bbox=(left, top, right, bottom))

    def take_center_screenshot(self, width: int = 600, height: int = 400):
        """
        화면 왼쪽 중앙 영역 스크린샷 (코레일 사이트가 왼쪽에 표시됨)

        Args:
            width: 캡처 너비
            height: 캡처 높이
        """
        screen_width, screen_height = pyautogui.size()
        # 왼쪽 절반의 중앙
        left = (screen_width // 2 - width) // 2
        top = (screen_height - height) // 2
        right = left + width
        bottom = top + height
        return ImageGrab.grab(bbox=(left, top, right, bottom))

    def save_debug_screenshot(self, img, label: str = ""):
        """디버깅용 스크린샷 저장"""
        if not self.debug:
            return
        self.debug_count += 1
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"debug_{self.debug_count:03d}_{timestamp}_{label}.png"
        img.save(filename)
        print(f"[DEBUG] 스크린샷 저장: {filename}")

    def get_average_color(self, img) -> tuple:
        """이미지의 평균 색상 계산"""
        try:
            pixels = list(img.getdata())
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return (r, g, b)
        except:
            return (0, 0, 0)

    def color_difference(self, color1: tuple, color2: tuple) -> int:
        """두 색상의 차이 계산 (0~765)"""
        return abs(color1[0] - color2[0]) + abs(color1[1] - color2[1]) + abs(color1[2] - color2[2])

    def compare_screenshots(self, img1, img2, threshold: float = 0.90) -> bool:
        """두 스크린샷 비교 (threshold 낮춤)"""
        if img1 is None or img2 is None:
            return False

        try:
            if img1.size != img2.size:
                return False

            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())

            sample_size = min(5000, len(pixels1))
            sample_indices = random.sample(range(len(pixels1)), sample_size)

            matches = 0
            for idx in sample_indices:
                # 색상 차이가 30 이하면 같은 픽셀로 판정 (약간의 차이 허용)
                diff = self.color_difference(pixels1[idx][:3], pixels2[idx][:3])
                if diff < 30:
                    matches += 1

            similarity = matches / sample_size
            return similarity >= threshold

        except Exception:
            return False

    def check_screen_changed(self, before_screenshot, check_area=None) -> bool:
        """
        화면이 변경되었는지 확인

        Args:
            before_screenshot: 이전 스크린샷
            check_area: 확인할 영역 (x, y, size) - None이면 전체 화면
        """
        # 더 긴 대기 시간 (페이지 로딩 고려)
        time.sleep(0.3)

        if check_area:
            x, y, size = check_area
            after_screenshot = self.take_screenshot_around(x, y, size)
            # 영역 스크린샷은 다시 찍어야 함
            before_region = self.take_screenshot_around(x, y, size)
            time.sleep(0.2)
            after_screenshot = self.take_screenshot_around(x, y, size)
            is_same = self.compare_screenshots(before_region, after_screenshot, threshold=0.85)
        else:
            after_screenshot = self.take_screenshot()
            is_same = self.compare_screenshots(before_screenshot, after_screenshot, threshold=0.90)

        return not is_same

    def capture_baseline(self):
        """
        기준 스크린샷 저장 (최초 1회)
        조회하기 클릭 후 호출하여 정상 상태의 화면을 저장
        """
        time.sleep(1.0)  # 페이지 로딩 대기
        self.baseline_screenshot = self.take_center_screenshot()
        self.baseline_color = self.get_average_color(self.baseline_screenshot)
        self.save_debug_screenshot(self.baseline_screenshot, "baseline")
        print(f"[INFO] 기준 스크린샷 저장 완료 (평균색상: {self.baseline_color})")

    def check_reservation_success(self, confirm_btn_pos) -> bool:
        """
        예매 성공 여부 확인 (최적화 버전)
        기준 스크린샷과 현재 화면 중앙을 비교
        "서비스 연결 대기중" 팝업 등 일시적 변화를 필터링

        Args:
            confirm_btn_pos: 예매 버튼 위치 (사용 안 함, 호환성 유지)
        """
        time.sleep(1.0)  # 페이지 반응 대기

        # 현재 화면 중앙 캡처
        current = self.take_center_screenshot()
        current_color = self.get_average_color(current)
        self.save_debug_screenshot(current, "check1")

        # 기준 스크린샷이 없으면 False
        if self.baseline_screenshot is None:
            print("[WARNING] 기준 스크린샷이 없습니다.")
            return False

        # 색상 차이 계산
        color_diff = self.color_difference(self.baseline_color, current_color)

        # 이미지 직접 비교
        is_same = self.compare_screenshots(self.baseline_screenshot, current, threshold=0.85)

        if self.debug:
            print(f"[DEBUG] 1차 확인 - 색상차이: {color_diff}, 동일: {is_same}")

        # 1차 변화 감지
        if not is_same or color_diff > 50:
            # 팝업이 사라질 때까지 대기 후 2차 확인
            print("[INFO] 화면 변화 감지, 2초 후 재확인...")
            time.sleep(2.0)

            # 2차 확인 - 여전히 변화가 있는지 확인
            current2 = self.take_center_screenshot()
            current_color2 = self.get_average_color(current2)
            self.save_debug_screenshot(current2, "check2")

            color_diff2 = self.color_difference(self.baseline_color, current_color2)
            is_same2 = self.compare_screenshots(self.baseline_screenshot, current2, threshold=0.85)

            if self.debug:
                print(f"[DEBUG] 2차 확인 - 색상차이: {color_diff2}, 동일: {is_same2}")

            # 2차에서도 여전히 다르면 진짜 성공
            if not is_same2 or color_diff2 > 50:
                print(f"[INFO] 화면 변화 확정! (색상차이: {color_diff2}, 동일: {is_same2})")
                return True
            else:
                print("[INFO] 일시적 팝업으로 판단, 계속 진행...")
                return False

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

    def setup_detection_coordinates(self):
        """로딩 감지용 좌표 설정"""
        print("\n[ 로딩 감지 좌표 설정 ]")
        print("로딩 상태를 감지하기 위한 좌표를 설정합니다.")
        print()
        print("[ 설명 ]")
        print("- 좌표1: 로딩 중=흰색, 로딩 완료=다른 색")
        print("- 좌표2: 로딩 완료=흰색 (회색 색상 지정 필요)")
        print("- 좌표3: 성공 시 특정 색상이 되는 위치")
        print()

        # 좌표1 설정
        print("1. '좌표1' 위치에 마우스를 올려놓고 Enter를 누르세요...")
        print("   (로딩 중=흰색, 로딩 완료=다른 색)")
        input()
        coord1 = pyautogui.position()
        color1 = self.get_pixel_color(coord1.x, coord1.y)
        print(f"   -> 좌표1: ({coord1.x}, {coord1.y}) - 현재 색상: RGB{color1}")

        # 좌표2 설정
        print()
        print("2. '좌표2' 위치에 마우스를 올려놓고 Enter를 누르세요...")
        print("   (로딩 완료=흰색)")
        input()
        coord2 = pyautogui.position()
        color2 = self.get_pixel_color(coord2.x, coord2.y)
        print(f"   -> 좌표2: ({coord2.x}, {coord2.y}) - 현재 색상: RGB{color2}")

        # 회색 색상 설정
        print()
        print("3. 좌표2의 '회색' 색상을 지정해주세요.")
        print("   (현재 좌표2 색상을 사용하려면 Enter, 직접 입력하려면 R,G,B 형식으로 입력)")
        gray_input = input("   회색 RGB (예: 128,128,128): ").strip()

        if gray_input:
            try:
                parts = gray_input.split(',')
                gray_color = (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                print("   [경고] 잘못된 형식, 현재 좌표2 색상을 사용합니다.")
                gray_color = color2
        else:
            gray_color = color2

        print(f"   -> 회색 색상: RGB{gray_color}")

        # 좌표3 설정
        print()
        print("4. '좌표3' 위치에 마우스를 올려놓고 Enter를 누르세요...")
        print("   (성공 시 특정 색상이 되는 위치)")
        input()
        coord3 = pyautogui.position()
        color3 = self.get_pixel_color(coord3.x, coord3.y)
        print(f"   -> 좌표3: ({coord3.x}, {coord3.y}) - 현재 색상: RGB{color3}")

        # 성공 색상 설정
        print()
        print("5. 좌표3의 '성공 색상'을 지정해주세요.")
        print("   (현재 좌표3 색상을 사용하려면 Enter, 직접 입력하려면 R,G,B 형식으로 입력)")
        success_input = input("   성공 색상 RGB (예: 255,0,0): ").strip()

        if success_input:
            try:
                parts = success_input.split(',')
                success_color = (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                print("   [경고] 잘못된 형식, 현재 좌표3 색상을 사용합니다.")
                success_color = color3
        else:
            success_color = color3

        print(f"   -> 성공 색상: RGB{success_color}")

        # 저장
        self.save_detection_config(coord1, coord2, coord3, gray_color, success_color)

        return coord1, coord2, coord3, gray_color, success_color

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
        """예약 루프 실행 (색상 기반 감지)"""
        max_attempts = self.config['reservation']['max_attempts']

        # 로딩 감지 좌표 확인/설정
        result = self.load_detection_config()
        if result[0] is None:
            print("\n[INFO] 로딩 감지 좌표가 설정되지 않았습니다.")
            coord1, coord2, coord3, gray_color, success_color = self.setup_detection_coordinates()
        else:
            coord1, coord2, coord3, gray_color, success_color = result
            print(f"\n[INFO] 로딩 감지 좌표 로드됨")
            print(f"  - 좌표1: ({coord1.x}, {coord1.y})")
            print(f"  - 좌표2: ({coord2.x}, {coord2.y})")
            print(f"  - 좌표3: ({coord3.x}, {coord3.y})")
            print(f"  - 회색: RGB{gray_color}")
            print(f"  - 성공색: RGB{success_color}")
            choice = input("이 설정을 사용할까요? (y/n): ").strip().lower()
            if choice != 'y':
                coord1, coord2, coord3, gray_color, success_color = self.setup_detection_coordinates()

        print(f"\n[INFO] 최대 시도 횟수: {max_attempts}회")
        print(f"[INFO] 등록된 열차: {len(reserve_btn_positions)}개 (순서대로 시도)")
        self.print_delay_info()
        print()
        print("[ 동작 순서 ]")
        print("1. 조회하기 클릭")
        print("2. 각 열차별 예약하기 → 예매 버튼 클릭")
        print("3. 색상 변화로 로딩 완료 감지 → 성공 시 종료")
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
                    # 예약하기 버튼 클릭
                    self.fast_click(reserve_btn_pos.x, reserve_btn_pos.y)
                    # 예매 버튼 클릭
                    self.fast_click(confirm_btn_pos.x, confirm_btn_pos.y)

                    # 색상 기반 로딩 완료 확인
                    if self.check_reservation_success_by_color(coord1, coord2, coord3, gray_color, success_color):
                        reservation_success = True
                        print(f"\n  [!] {train_idx}번 열차 - 예매 성공!")
                        print()
                        print("*" * 60)
                        print(f"  축하합니다! {train_idx}번 열차 예매 성공!")
                        print("  결제를 진행해주세요.")
                        print("*" * 60)

                        # 성공 스크린샷 저장
                        success_img = self.take_screenshot()
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"success_{timestamp}.png"
                        success_img.save(filename)
                        print(f"[INFO] 성공 스크린샷 저장: {filename}")

                        # 소리 알림
                        if self.config.get('notification', {}).get('sound', False):
                            for _ in range(5):
                                print('\a', end='', flush=True)
                                time.sleep(0.3)

                        # Discord 알림 (스크린샷 첨부)
                        self.discord_send_message(
                            f"🎉 KTX 예매 성공! {train_idx}번 열차 예매가 완료되었습니다. 결제를 진행해주세요!",
                            image_path=filename
                        )
                        break

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
    import sys
    debug_mode = "--debug" in sys.argv
    if debug_mode:
        print("[DEBUG] 디버깅 모드 활성화 - 스크린샷이 파일로 저장됩니다.")
    auto = KorailAutoGUI(debug=debug_mode)
    auto.run()
