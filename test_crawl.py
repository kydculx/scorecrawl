"""
headless 크롤링 테스트 스크립트
프리미어리그 2025-2026, 3개 라운드만 테스트
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor

BASE_URL = "https://football.scoreman123.com"

def test():
    url = f"{BASE_URL}/league/2025-2026/36"
    league_name = "프리미어리그"
    season_name = "2025-2026"
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    crawler = ScoreCrawler(log_callback=print)
    df, title, _ = crawler.crawl(url, max_rounds=3)

    if df.empty:
        print("\n❌ 수집된 데이터가 없습니다!")
        return

    print(f"\n✅ 총 {len(df)}개 매치 수집")
    print(f"\n컬럼: {list(df.columns)}")
    print(f"\n=== 미리보기 (처음 5행) ===")
    print(df.head(5).to_string(index=False))

    DataProcessor.save_results(
        df, title, print,
        league_name=league_name, season_name=season_name
    )

    safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    output_file = f"{safe_title}.xlsx"
    if os.path.exists(output_file):
        print(f"\n✅ 엑셀 저장 완료: {output_file}")
    else:
        print(f"\n❌ 엑셀 파일을 찾을 수 없음: {output_file}")

if __name__ == "__main__":
    test()
