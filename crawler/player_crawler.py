import re
import pandas as pd
from playwright.sync_api import sync_playwright
from .data_processor import DataProcessor
from utils.constants import PLAYER_STATS_HEADER
from io import StringIO

class PlayerCrawler:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def get_players(self, player_list_url, team_name=None):
        """선수 목록 페이지에서 선수 목록 및 요약 통계 추출"""
        players = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.log(f"선수 목록 수집 중: {player_list_url}")
                page.goto(player_list_url)
                
                try:
                    page.wait_for_load_state("networkidle")
                    # 사용자가 제공한 HTML 구조에 맞는 테이블 선택자
                    page.wait_for_selector("#div_Table2 table", timeout=5000)
                except:
                    pass
                
                # 테이블 행 파싱 (div_Table2 내부의 테이블)
                rows = page.locator("#div_Table2 table tr").all()
                seen_players = set()
                
                for row in rows:
                    try:
                        cells = row.locator("td").all()
                        if not cells: continue
                        
                        # 선수 링크 찾기 (이름이 있는 셀 - 보통 두번째 td)
                        # HTML 구조상: 랭킹(td), 선수(td > div > a), 국가(td) ...
                        link = row.locator("a[href*='/player/']").first
                        if not link.count(): continue
                        
                        name = link.inner_text().strip()
                        href = link.get_attribute("href")
                        
                        if not name or not href: continue
                        if name in seen_players: continue
                        if name.isdigit(): continue
                        
                        # 팀 필터링 (제공된 HTML에는 팀 정보가 없으므로 필터링 제외)
                        # 만약 팀별로 다른 URL을 사용해야 한다면 구조 변경 필요
                        # 현재는 해당 페이지의 모든 선수를 가져옴
                        
                        # 요약 통계 추출 (이미지/HTML 컬럼 기준)
                        # 0:랭킹, 1:선수, 2:국가, 3:골인, 4:골인/승, 5:골인/무, 6:골인/패, 7:옐로, 8:레드
                        stats = {}
                        if len(cells) >= 9:
                            stats["랭킹"] = cells[0].inner_text().strip()
                            stats["선수"] = name
                            stats["국가"] = cells[2].inner_text().strip()
                            stats["골인"] = cells[3].inner_text().strip()
                            stats["골인/승"] = cells[4].inner_text().strip()
                            stats["골인/무"] = cells[5].inner_text().strip()
                            stats["골인/패"] = cells[6].inner_text().strip()
                            stats["옐로카드"] = cells[7].inner_text().strip()
                            stats["레드카드"] = cells[8].inner_text().strip()
                        
                        players.append({
                            "name": name, 
                            "url": href,
                            "summary_stats": stats
                        })
                        seen_players.add(name)
                    except:
                        continue
                        
                self.log(f"총 {len(players)}명의 선수를 찾았습니다.")
                
            except Exception as e:
                self.log(f"선수 목록 수집 실패: {e}")
            finally:
                browser.close()
                
        return sorted(players, key=lambda x: x['name'])

    def crawl_player_data(self, player_url, player_name, summary_stats=None):
        """선수 상세 페이지에서 데이터 크롤링 (요약 통계 포함)"""
        result_data = {
            "stats": {}
        }
        
        # 요약 통계가 있으면 먼저 추가
        if summary_stats:
            df_summary = pd.DataFrame([summary_stats])
            # 컬럼 순서 정렬
            cols = [c for c in PLAYER_STATS_HEADER if c in df_summary.columns]
            if cols:
                df_summary = df_summary[cols]
            result_data["stats"]["요약_정보"] = df_summary
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.log(f"선수 데이터 수집 시작: {player_name} ({player_url})")
                page.goto(player_url)
                
                page.wait_for_load_state("networkidle")
                
                # 통계 테이블 수집
                content = page.content()
                try:
                    dfs = pd.read_html(StringIO(content))
                    self.log(f"페이지에서 {len(dfs)}개의 테이블을 찾았습니다.")
                    
                    for i, df in enumerate(dfs):
                        df = df.dropna(how='all').dropna(axis=1, how='all')
                        
                        if not df.empty:
                            key = f"Table_{i+1}"
                            cols = [str(c).lower() for c in df.columns]
                            col_str = "".join(cols)
                            
                            if "season" in col_str or "시즌" in col_str:
                                key = "시즌_기록"
                            elif "match" in col_str or "경기" in col_str:
                                key = "경기_기록"
                                
                            if key in result_data["stats"]:
                                key = f"{key}_{i+1}"
                                
                            result_data["stats"][key] = df
                    
                    self.log(f"데이터 수집 완료: {list(result_data['stats'].keys())}")
                    
                except Exception as e:
                    self.log(f"데이터 파싱 실패: {e}")
                    
            except Exception as e:
                self.log(f"크롤링 에러: {e}")
            finally:
                browser.close()
                
        return result_data

