import argparse
import sys
import os

# 현재 디렉토리를 sys.path에 추가하여 모듈을 원활히 불러오도록 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.constants import LEAGUE_DATA
from crawler.season_fetcher import fetch_seasons, build_season_url
from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor

def main():
    parser = argparse.ArgumentParser(description="ScoreCrawl CLI Runner")
    parser.add_argument("--league", type=str, required=True, help="크롤링할 리그명 (예: '프리미어리그')")
    parser.add_argument("--season", type=str, default="latest", help="크롤링할 시즌명 (예: '2025-2026', 'latest')")
    parser.add_argument("--max-rounds", type=int, default=None, help="수집할 최대 라운드 수 (테스트용)")
    parser.add_argument("--domain", type=str, default="scoreman123.com", help="기본 도메인")
    
    args = parser.parse_args()
    
    # 1. 리그 데이터 매핑 확인
    league_info = next((item for item in LEAGUE_DATA if item["name"] == args.league), None)
    if not league_info:
        print(f"❌ 지원하지 않는 리그명입니다: {args.league}")
        print(f"지원 리그 목록: {[item['name'] for item in LEAGUE_DATA]}")
        sys.exit(1)
        
    league_url = league_info["url"]
    league_name = args.league
    
    # 2. 크롤링 대상 시즌 및 URL 결정
    target_season_name = args.season
    target_url = ""
    
    if target_season_name == "latest" or not target_season_name:
        # 최신 시즌을 동적으로 조회
        print(f"🔄 {league_name}의 최신 시즌 정보를 조회 중...")
        seasons = fetch_seasons(league_url, domain=args.domain, max_seasons=1)
        if not seasons:
            print("❌ 시즌 정보를 가져오지 못했습니다. 기본 리그 URL로 크롤링을 시도합니다.")
            target_url = f"https://football.{args.domain}{league_url}"
            target_season_name = "latest"
        else:
            target_url = f"https://football.{args.domain}{seasons[0]['url']}"
            target_season_name = seasons[0]["name"]
    else:
        # 특정 시즌 지정
        season_path = build_season_url(league_url, target_season_name, first_season=False)
        target_url = f"https://football.{args.domain}{season_path}"
        
    print(f"🚀 크롤링 타겟 URL: {target_url}")
    print(f"📂 대상 리그: {league_name} / 대상 시즌: {target_season_name}")
    if args.max_rounds:
        print(f"🔢 최대 수집 라운드 제한: {args.max_rounds}")
        
    # 3. 크롤러 구동
    crawler = ScoreCrawler(log_callback=print)
    try:
        df, title, _ = crawler.crawl(target_url, max_rounds=args.max_rounds, default_title=league_name)
        
        if df.empty:
            print("❌ 수집된 데이터가 없습니다.")
            sys.exit(0)
            
        custom_title = f"{league_name}_{target_season_name}"
        
        # 4. 데이터 저장 (엑셀 및 Supabase DB 적재)
        filename = DataProcessor.save_results(
            df, custom_title, log_callback=print,
            league_name=league_name,
            season_name=target_season_name
        )
        
        if filename:
            print(f"✨ 크롤링 및 DB 적재 완료: {filename}")
        else:
            print("❌ 데이터 처리 중 오류가 발생했거나 저장할 데이터가 없습니다.")
            
    except Exception as e:
        print(f"💥 크롤링 중 치명적 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
