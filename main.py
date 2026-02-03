#!/usr/bin/env python3
"""
코레일 KTX 취소표 자동 예약 프로그램
실행 방법: python main.py [--config CONFIG_PATH]
"""

import argparse
import os
import sys


def check_config_file(config_path: str) -> bool:
    """설정 파일 존재 확인"""
    if not os.path.exists(config_path):
        print(f"[ERROR] 설정 파일을 찾을 수 없습니다: {config_path}")
        print("\n다음 단계를 따라주세요:")
        print("1. config.example.yaml 파일을 config.yaml로 복사하세요")
        print("   cp config.example.yaml config.yaml")
        print("2. config.yaml 파일을 열어 로그인 정보와 여정 정보를 입력하세요")
        return False
    return True


def main():
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description="코레일 KTX 취소표 자동 예약 프로그램"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="설정 파일 경로 (기본값: config.yaml)"
    )
    args = parser.parse_args()

    # 설정 파일 확인
    if not check_config_file(args.config):
        sys.exit(1)

    # 메인 실행
    from korail import KorailReservation

    print("=" * 50)
    print("   코레일 KTX 취소표 자동 예약 프로그램")
    print("=" * 50)
    print()
    print("[INFO] 프로그램을 시작합니다...")
    print("[INFO] 종료하려면 Ctrl+C를 누르세요.")
    print()

    reservation = KorailReservation(config_path=args.config)
    reservation.run()


if __name__ == "__main__":
    main()
