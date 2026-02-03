"""
코레일 KTX 취소표 자동 예약 프로그램
"""

import time
import yaml
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException
)
from webdriver_manager.chrome import ChromeDriverManager


class KorailReservation:
    """코레일 KTX 예약 자동화 클래스"""

    KORAIL_URL = "https://www.korail.com/"
    KORAIL_LOGIN_URL = "https://www.korail.com/ticket/login/loginForm.do"
    KORAIL_SEARCH_URL = "https://www.korail.com/ticket/main/mainForm.do"

    # 역 코드 매핑 (주요 역)
    STATION_CODES = {
        "서울": "0001",
        "용산": "0015",
        "영등포": "0020",
        "광명": "0502",
        "수원": "0061",
        "천안아산": "0502",
        "오송": "0297",
        "대전": "0010",
        "김천구미": "0507",
        "동대구": "0015",
        "경주": "0508",
        "울산": "0509",
        "부산": "0020",
        "포항": "0515",
        "익산": "0030",
        "광주송정": "0036",
        "목포": "0041",
        "여수엑스포": "0059",
        "전주": "0045",
        "강릉": "0115",
    }

    def __init__(self, config_path: str = "config.yaml"):
        """
        초기화

        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.driver = None
        self.wait = None

    def _load_config(self, config_path: str) -> dict:
        """설정 파일 로드"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _setup_driver(self):
        """Selenium WebDriver 설정"""
        chrome_options = Options()

        # 옵션 설정
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # 브라우저 감지 방지
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        # WebDriver 초기화
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        # navigator.webdriver 속성 숨기기
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        print("[INFO] 브라우저가 시작되었습니다.")

    def login(self) -> bool:
        """
        코레일 로그인

        Returns:
            bool: 로그인 성공 여부
        """
        try:
            print("[INFO] 로그인 페이지로 이동합니다...")
            self.driver.get(self.KORAIL_LOGIN_URL)
            time.sleep(2)

            # 로그인 정보 입력
            user_id = self.config['login']['id']
            password = self.config['login']['password']

            # ID 입력
            id_input = self.wait.until(
                EC.presence_of_element_located((By.ID, "txtMember"))
            )
            id_input.clear()
            id_input.send_keys(user_id)

            # 비밀번호 입력
            pw_input = self.driver.find_element(By.ID, "txtPwd")
            pw_input.clear()
            pw_input.send_keys(password)

            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "button.btn_login")
            login_btn.click()

            time.sleep(3)

            # 로그인 성공 확인
            if "login" not in self.driver.current_url.lower():
                print("[SUCCESS] 로그인 성공!")
                return True
            else:
                print("[ERROR] 로그인 실패. 아이디/비밀번호를 확인하세요.")
                return False

        except TimeoutException:
            print("[ERROR] 로그인 페이지 로딩 시간 초과")
            return False
        except Exception as e:
            print(f"[ERROR] 로그인 중 오류 발생: {e}")
            return False

    def search_trains(self) -> bool:
        """
        열차 조회

        Returns:
            bool: 조회 성공 여부
        """
        try:
            print("[INFO] 열차 조회 페이지로 이동합니다...")
            self.driver.get(self.KORAIL_SEARCH_URL)
            time.sleep(2)

            journey = self.config['journey']

            # 출발역 입력
            dep_station = self.wait.until(
                EC.presence_of_element_located((By.ID, "start"))
            )
            dep_station.clear()
            dep_station.send_keys(journey['departure_station'])
            time.sleep(0.5)

            # 도착역 입력
            arr_station = self.driver.find_element(By.ID, "get")
            arr_station.clear()
            arr_station.send_keys(journey['arrival_station'])
            time.sleep(0.5)

            # 날짜 설정
            date_str = journey['date']
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # 날짜 입력 필드 찾기 및 설정
            date_input = self.driver.find_element(By.ID, "s_date")
            self.driver.execute_script(
                f"arguments[0].value = '{date_obj.strftime('%Y%m%d')}'",
                date_input
            )

            # 시간 설정
            time_str = journey['time']
            hour = time_str.split(':')[0]

            # 시간 선택
            time_select = Select(self.driver.find_element(By.ID, "s_hour"))
            time_select.select_by_value(hour)

            # 조회 버튼 클릭
            search_btn = self.driver.find_element(By.CSS_SELECTOR, "button.btn_search")
            search_btn.click()

            time.sleep(3)
            print("[SUCCESS] 열차 조회 완료!")
            return True

        except Exception as e:
            print(f"[ERROR] 열차 조회 중 오류 발생: {e}")
            return False

    def check_availability(self) -> list:
        """
        예약 가능한 열차 확인

        Returns:
            list: 예약 가능한 열차 목록
        """
        available_trains = []
        seat_type = self.config['seat']['type']

        try:
            # 열차 목록 테이블 찾기
            train_rows = self.driver.find_elements(
                By.CSS_SELECTOR, "table.tbl_train tbody tr"
            )

            for idx, row in enumerate(train_rows):
                try:
                    # KTX인지 확인
                    train_type = row.find_element(By.CSS_SELECTOR, "td.train_type").text
                    if "KTX" not in train_type:
                        continue

                    # 출발/도착 시간
                    dep_time = row.find_element(By.CSS_SELECTOR, "td.dep_time").text
                    arr_time = row.find_element(By.CSS_SELECTOR, "td.arr_time").text

                    # 좌석 상태 확인
                    if seat_type == "special":
                        # 특실
                        seat_cell = row.find_element(By.CSS_SELECTOR, "td.special")
                    else:
                        # 일반실
                        seat_cell = row.find_element(By.CSS_SELECTOR, "td.general")

                    seat_status = seat_cell.text.strip()

                    # 예약 가능 여부 확인
                    if "예약하기" in seat_status or "좌석선택" in seat_status:
                        available_trains.append({
                            'index': idx,
                            'type': train_type,
                            'departure': dep_time,
                            'arrival': arr_time,
                            'seat_element': seat_cell
                        })
                        print(f"[FOUND] 예약 가능: {train_type} {dep_time} -> {arr_time}")

                except NoSuchElementException:
                    continue

        except Exception as e:
            print(f"[ERROR] 좌석 확인 중 오류: {e}")

        return available_trains

    def refresh_search(self):
        """검색 결과 새로고침"""
        try:
            # 조회하기 버튼 다시 클릭 또는 페이지 새로고침
            refresh_btn = self.driver.find_element(
                By.CSS_SELECTOR, "button.btn_refresh, button.btn_search"
            )
            refresh_btn.click()
            time.sleep(2)
        except:
            # 버튼을 못 찾으면 페이지 새로고침
            self.driver.refresh()
            time.sleep(3)

    def reserve_ticket(self, train_info: dict) -> bool:
        """
        티켓 예약

        Args:
            train_info: 예약할 열차 정보

        Returns:
            bool: 예약 성공 여부
        """
        try:
            print(f"[INFO] 예약 시도: {train_info['type']} {train_info['departure']}")

            # 예약하기 버튼 클릭
            seat_element = train_info['seat_element']
            reserve_btn = seat_element.find_element(By.TAG_NAME, "a")
            reserve_btn.click()

            time.sleep(2)

            # 예약 확인 페이지에서 최종 예약 버튼 클릭
            # (실제 코레일 사이트 구조에 따라 수정 필요)
            confirm_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn_reserve"))
            )
            confirm_btn.click()

            time.sleep(3)

            # 예약 성공 확인
            if "complete" in self.driver.current_url.lower() or "결제" in self.driver.page_source:
                print("[SUCCESS] 예약이 완료되었습니다!")
                return True
            else:
                print("[WARNING] 예약 진행 중... 결제 페이지를 확인하세요.")
                return True

        except ElementClickInterceptedException:
            print("[ERROR] 다른 사용자가 먼저 예약했습니다.")
            return False
        except Exception as e:
            print(f"[ERROR] 예약 중 오류 발생: {e}")
            return False

    def run(self):
        """메인 실행 루프"""
        try:
            # 브라우저 설정
            self._setup_driver()

            # 로그인
            if not self.login():
                print("[ERROR] 로그인 실패. 프로그램을 종료합니다.")
                return

            # 열차 조회
            if not self.search_trains():
                print("[ERROR] 열차 조회 실패. 프로그램을 종료합니다.")
                return

            # 예약 시도 루프
            reservation_config = self.config['reservation']
            refresh_interval = reservation_config['refresh_interval']
            max_attempts = reservation_config['max_attempts']

            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                print(f"\n[INFO] 시도 {attempt}/{max_attempts} - {datetime.now().strftime('%H:%M:%S')}")

                # 예약 가능한 열차 확인
                available = self.check_availability()

                if available:
                    # 첫 번째 예약 가능한 열차 예약 시도
                    if self.reserve_ticket(available[0]):
                        print("\n" + "=" * 50)
                        print("[SUCCESS] 예약 성공! 결제를 진행하세요.")
                        print("=" * 50)

                        # 알림
                        if self.config.get('notification', {}).get('sound', False):
                            print('\a' * 5)  # 비프음

                        input("프로그램을 종료하려면 Enter를 누르세요...")
                        return

                # 새로고침 대기
                print(f"[INFO] {refresh_interval}초 후 새로고침...")
                time.sleep(refresh_interval)
                self.refresh_search()

            print("[INFO] 최대 시도 횟수에 도달했습니다.")

        except KeyboardInterrupt:
            print("\n[INFO] 사용자에 의해 중단되었습니다.")
        finally:
            if self.driver:
                self.driver.quit()
                print("[INFO] 브라우저가 종료되었습니다.")


if __name__ == "__main__":
    reservation = KorailReservation()
    reservation.run()
