import re
import pandas as pd
from playwright.sync_api import sync_playwright
from .data_processor import DataProcessor
from .player_crawler import PlayerCrawler
from utils.constants import STATS_COLUMNS, TEAM_PLAYER_URLS
from io import StringIO

class TeamCrawler:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def get_teams(self, league_url):
        """리그 페이지에서 팀 목록을 추출"""
        teams = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                self.log(f"팀 목록 수집 중: {league_url}")
                page.goto(league_url)
                
                try:
                    page.wait_for_selector(".lei_table, #Table3", timeout=5000)
                except:
                    self.log("순위표를 찾을 수 없습니다. 다른 선택자를 시도합니다.")
                
                links = page.locator("a[href*='/team/']").all()
                seen_teams = set()
                
                for link in links:
                    try:
                        # 팀 이름 정제 (이름 뒤에 붙은 숫자나 태그 제거)
                        name = link.inner_text().strip()
                        # 정규식으로 숫자만 있는 패턴 제거 (예: 맨체스터 시티1 -> 맨체스터 시티)
                        # 또는 특정 태그 안의 숫자 제거
                        name = re.sub(r'\d+$', '', name).strip()
                        
                        href = link.get_attribute("href")
                        
                        if not name or not href: continue
                        if name in seen_teams: continue
                        
                        teams.append({"name": name, "url": href})
                        seen_teams.add(name)
                    except:
                        continue
                        
                self.log(f"총 {len(teams)}개의 팀을 찾았습니다.")
                
            except Exception as e:
                self.log(f"팀 목록 수집 실패: {e}")
            finally:
                browser.close()
                
        return sorted(teams, key=lambda x: x['name'])

    def crawl_team_data(self, team_url, team_name):
        """팀 상세 페이지에서 통계 및 경기 결과 데이터 크롤링"""
        result_data = {
            "stats": {}
        }
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # 선수 데이터 수집 (URL이 상수에 정의된 경우)
                if team_name in TEAM_PLAYER_URLS:
                    try:
                        player_path = TEAM_PLAYER_URLS[team_name]
                        # team_url에서 도메인 추출
                        base_url = "/".join(team_url.split("/")[:3])
                        player_full_url = f"{base_url}{player_path}"
                        
                        self.log(f"선수 데이터 수집 시도: {player_full_url}")
                        pc = PlayerCrawler(self.log_callback)
                        players = pc.get_players(player_full_url)
                        result_data["players"] = players
                        self.log(f"선수 데이터 수집 완료: {len(players)}명")
                    except Exception as e:
                        self.log(f"선수 데이터 수집 실패: {e}")

                self.log(f"팀 데이터 수집 시작: {team_name} ({team_url})")
                page.goto(team_url)
                
                # 페이지 로딩 대기
                page.wait_for_load_state("networkidle")
                try:
                    page.wait_for_selector("table", timeout=5000)
                except:
                    pass

                # 1. 통계 테이블 수집 (pd.read_html 사용)
                content = page.content()
                try:
                    dfs = pd.read_html(StringIO(content))
                    self.log(f"페이지에서 {len(dfs)}개의 테이블을 찾았습니다.")
                    
                    # 테이블 분류
                    for i, df in enumerate(dfs):
                        # 데이터 정제 (NaN 제거)
                        df = df.dropna(how='all').dropna(axis=1, how='all')
                        
                        # 테이블 식별 로직 (컬럼명 기반)
                        cols = [str(c).replace(" ", "") for c in df.columns]
                        col_str = "".join(cols)
                        
                        # 특정 키워드로 매핑 (이미지 참고)
                        # 리그 승점: 경기, 승, 무승부, 패, 득점, 실점...
                        if "경기" in col_str and "승" in col_str and "무승부" in col_str and "패" in col_str and "승점" in col_str:
                            if "리그_승점" not in result_data["stats"]:
                                result_data["stats"]["리그_승점"] = df
                            else:
                                result_data["stats"]["전반전_리그_승점"] = df
                                
                        # 핸디캡: 경기, 주기, 핸무/팹무, 받기...
                        elif "경기" in col_str and "주기" in col_str and ("핸무" in col_str or "팹무" in col_str or "받기" in col_str):
                            if "핸디캡_순위" not in result_data["stats"]:
                                result_data["stats"]["핸디캡_순위"] = df
                            else:
                                result_data["stats"]["전반_핸디캡"] = df
                                
                        # 오버/언더: 경기, 오버, 무승부, 언더...
                        elif "경기" in col_str and "오버" in col_str and "언더" in col_str:
                            if "오버_순위" not in result_data["stats"]:
                                result_data["stats"]["오버_순위"] = df
                            else:
                                result_data["stats"]["전반_오버_언더"] = df
                    
                    self.log(f"통계 테이블 분류 완료: {list(result_data['stats'].keys())}")
                    
                except Exception as e:
                    self.log(f"통계 테이블 파싱 실패: {e}")

            except Exception as e:
                self.log(f"크롤링 에러: {e}")
            finally:
                browser.close()
                
        return result_data
