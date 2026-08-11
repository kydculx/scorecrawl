"""
이어받기 크롤링: Supabase에 저장된 마지막 라운드부터 현재까지 자동으로 크롤링

사용법:
    python crawl_resume.py --league "프리미어리그"
    python crawl_resume.py --all          # 모든 리그 순회
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor
from crawler.season_fetcher import fetch_seasons
from utils.constants import LEAGUE_DATA, LEAGUE_TABLE
from utils.supabase_helper import get_max_round

BASE_URL = "https://football.scoreman123.com"
DOMAIN = "scoreman123.com"


def crawl_league(league_name: str, league_url: str, dry_run: bool = False):
    """특정 리그의 이어받기 크롤링 실행"""
    seasons = fetch_seasons(league_url, DOMAIN)
    if not seasons:
        print(f"[{league_name}] 시즌 목록을 가져올 수 없습니다.")
        return False

    latest = seasons[0]
    season_name = latest["name"]
    url = f"{BASE_URL}{latest['url']}"

    max_r = get_max_round(league_name, season_name)
    start = max_r if max_r is not None else 1

    print(f"\n[{league_name}] [{season_name}]")
    if max_r is None:
        print(f"  DB에 저장된 데이터 없음 → 1라운드부터 시작")
    else:
        print(f"  DB 저장: {max_r}라운드까지 → {max_r}라운드부터 재개 (중간 저장분 보충)")

    table_name = LEAGUE_TABLE.get(league_name)
    if dry_run:
        print(f"  [Dry-Run] 크롤링 URL: {url}")
        print(f"  [Dry-Run] 시작 라운드: {start}")
        if table_name:
            print(f"  [Dry-Run] 대상 테이블: {table_name}")
        return True

    crawler = ScoreCrawler()
    df, title, _ = crawler.crawl(url, start_round=start, default_title=league_name)

    if df.empty:
        print(f"  수집된 데이터가 없습니다.")
        return False

    DataProcessor.save_results(
        df, f"{league_name}_{season_name}", print,
        league_name=league_name, season_name=season_name
    )
    return True


def main():
    parser = argparse.ArgumentParser(description="이어받기 크롤링")
    parser.add_argument("--league", help="리그명 (예: '프리미어리그')")
    parser.add_argument("--all", action="store_true", help="모든 리그 순회")
    parser.add_argument("--dry-run", action="store_true", help="실제 크롤링 없이 계획만 출력")
    args = parser.parse_args()

    if args.all:
        targets = [(d["name"], d["url"]) for d in LEAGUE_DATA]
    elif args.league:
        found = [d for d in LEAGUE_DATA if d["name"] == args.league]
        if not found:
            available = ", ".join(d["name"] for d in LEAGUE_DATA)
            print(f"리그 '{args.league}'을(를) 찾을 수 없습니다. 가능: {available}")
            sys.exit(1)
        targets = [(found[0]["name"], found[0]["url"])]
    else:
        parser.print_help()
        sys.exit(1)

    success = 0
    for name, url in targets:
        if crawl_league(name, url, args.dry_run):
            success += 1

    print(f"\n{'='*50}")
    print(f"완료: {success}/{len(targets)} 리그 성공")


if __name__ == "__main__":
    main()
