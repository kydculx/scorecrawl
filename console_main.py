"""
콘솔 크롤링 모드

사용법:
    python console_main.py all           # 모든 리그 × 모든 시즌 전체 크롤링 (1회)
    python console_main.py last          # DB에 저장된 마지막 라운드부터 이어서 (1회)
    python console_main.py all 60        # 60분마다 전체 크롤링 반복
    python console_main.py last 30       # 30분마다 이어서 크롤링 반복
"""
import sys
import os
import time
import signal
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor
from crawler.season_fetcher import fetch_seasons
from utils.constants import LEAGUE_DATA
from crawl_resume import crawl_league

BASE_URL = "https://football.scoreman123.com"
DOMAIN = "scoreman123.com"

_stop = False


def _handle_signal(signum, frame):
    global _stop
    _stop = True
    print("\n[종료 요청] 현재 크롤링 완료 후 종료합니다...")


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def crawl_all_league(league_name: str, league_url: str) -> bool:
    """리그의 모든 시즌 전체 라운드 크롤링"""
    seasons = fetch_seasons(league_url, DOMAIN)
    if not seasons:
        print(f"[{league_name}] 시즌 목록을 가져올 수 없습니다.")
        return False

    print(f"\n[{league_name}] 전체 {len(seasons)}개 시즌 크롤링 시작")
    success = 0
    for i, season in enumerate(seasons):
        if _stop:
            print(f"  [중지] 남은 시즌 스킵")
            break

        season_name = season["name"]
        url = f"{BASE_URL}{season['url']}"
        pct = (i + 1) / len(seasons) * 100
        print(f"\n  [{i+1}/{len(seasons)}] {season_name} 크롤링 중... ({pct:.0f}%)")

        try:
            crawler = ScoreCrawler()
            df, title, _ = crawler.crawl(url, default_title=league_name)

            if _stop:
                print(f"  [중지] {season_name} 저장 생략")
                break

            if df.empty:
                print(f"  [건너뜀] {season_name} - 데이터 없음")
                continue

            custom_title = f"{league_name}_{season_name}"
            filename = DataProcessor.save_results(
                df, custom_title, print,
                league_name=league_name, season_name=season_name
            )
            if filename:
                print(f"  [완료] {season_name} → {filename}")
                success += 1
        except Exception as e:
            print(f"  [오류] {season_name} - {e}")

    print(f"[{league_name}] 완료: {success}/{len(seasons)} 시즌 성공")
    return success > 0


def run_all_once():
    """모든 리그 전체 크롤링 1회"""
    print(f"[{now_str()}] 전체 크롤링 시작 (all 모드)")
    targets = [(d["name"], d["url"]) for d in LEAGUE_DATA]
    success = 0
    for name, url in targets:
        if _stop:
            break
        if crawl_all_league(name, url):
            success += 1
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 전체 크롤링 종료: {success}/{len(targets)} 리그 성공")


def run_last_once():
    """모든 리그 이어서 크롤링 1회"""
    print(f"[{now_str()}] 이어서 크롤링 시작 (last 모드)")
    targets = [(d["name"], d["url"]) for d in LEAGUE_DATA]
    success = 0
    for name, url in targets:
        if _stop:
            break
        if crawl_league(name, url):
            success += 1
    print(f"\n{'='*50}")
    print(f"[{now_str()}] 이어서 크롤링 종료: {success}/{len(targets)} 리그 성공")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("all", "last"):
        print(__doc__)
        sys.exit(1)

    mode = sys.argv[1]
    interval = None
    if len(sys.argv) >= 3:
        try:
            interval = int(sys.argv[2])
            if interval <= 0:
                raise ValueError
        except ValueError:
            print(f"타이머는 양의 정수(분)여야 합니다: '{sys.argv[2]}'")
            sys.exit(1)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    run_fn = run_all_once if mode == "all" else run_last_once

    if interval is None:
        run_fn()
        sys.exit(0)

    print(f"[{now_str()}] 타이머 설정: 매 {interval}분마다 '{mode}' 크롤링 반복")
    while not _stop:
        run_fn()
        if _stop:
            break
        next_time = datetime.fromtimestamp(time.time() + interval * 60).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str()}] 다음 실행 예정: {next_time} (매 {interval}분)")

        # 재시작 대기: 1분 단위로 남은 시간 표시 (파일 로그 리다이렉트 호환)
        total_secs = interval * 60
        for remaining in range(total_secs, 0, -1):
            if _stop:
                break
            time.sleep(1)
            if remaining % 60 == 0:
                print(f"[{now_str()}] 재시작까지 {remaining // 60}분 남음")
        print(f"[{now_str()}] 재시작")

    print(f"[{now_str()}] 종료됨")


if __name__ == "__main__":
    main()
