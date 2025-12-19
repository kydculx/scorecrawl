import re
import pandas as pd
from playwright.sync_api import sync_playwright
from .data_processor import DataProcessor

class ScoreCrawler:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.companies = []

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def crawl(self, url, max_rounds=None):
        data_list = []
        league_title = "Unknown"
        
        # 도메인 확인
        is_nowgoal = "nowgoal.com" in url

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = context.new_page()

            try:
                self.log(f"사이트 접속 중: {url}")
                page.goto(url)
                
                try:
                    league_title_full = page.locator(".info_title").inner_text().strip()
                    league_title = league_title_full.split('\n')[0].strip()
                    self.log(f"리그: {league_title}")
                except:
                    self.log("리그 제목을 찾을 수 없습니다.")

                # 라운드 정보
                page.wait_for_selector("#Table2", timeout=5000)
                round_elements = page.locator("#Table2 td[onclick*='changeRound']").all()
                round_texts = [el.inner_text().strip() for el in round_elements if el.inner_text().strip().isdigit()]
                
                try:
                    current_round_el = page.locator("#Table2 td.round_now").first
                    current_round = int(current_round_el.inner_text().strip())
                    round_texts.append(str(current_round))
                except:
                    current_round = 38

                round_texts = sorted(list(set(round_texts)), key=int)
                round_texts = [r for r in round_texts if int(r) <= current_round]
                
                if max_rounds:
                    self.log(f"테스트 모드: {max_rounds}개 라운드만 수집")
                    round_texts = round_texts[:max_rounds]

                # 배당 회사 확인
                company_options = page.locator("#oddsCompany option").all()
                self.companies = []
                for opt in company_options:
                    val = opt.get_attribute("value")
                    text = opt.inner_text().strip()
                    if val: self.companies.append((val, text))
                
                self.log(f"수집 대상 회사: {[n for v, n in self.companies]}")

                # 라운드별 순회
                for round_num in round_texts:
                    self.log(f"\n[{round_num} 라운드] 수집 시작")
                    try:
                        page.locator("#Table2 td").filter(has_text=re.compile(rf"^\s*{round_num}\s*$")).first.click()
                        page.wait_for_timeout(1000)
                        
                        for comp_val, comp_name in self.companies:
                            self._process_company_round(page, round_num, comp_val, comp_name, data_list, is_nowgoal)
                            
                    except Exception as e:
                        self.log(f"라운드 {round_num} 에러: {e}")

            except Exception as e:
                self.log(f"크롤링 치명적 오류: {e}")
            finally:
                browser.close()

        return pd.DataFrame(data_list), league_title, [n for v, n in self.companies]

    def _process_company_round(self, page, round_num, comp_val, comp_name, data_list, is_nowgoal=False):
        try:
            page.select_option("#oddsCompany", comp_val)
            page.wait_for_timeout(50)
            
            rows = page.locator("tr").all()
            count = 0
            
            for row in rows:
                try:
                    cells = row.locator("td").all()
                    if len(cells) < 5: continue
                    
                    # 데이터 파싱
                    date_raw = cells[1].inner_text().strip().split('\n')
                    date_val = date_raw[0].strip().replace('-', '.')
                    
                    # nowgoal.com 인 경우 날짜 형식 변경 (일.월 -> 월.일)
                    if is_nowgoal and '.' in date_val:
                        parts = date_val.split('.')
                        if len(parts) >= 2:
                            # 25.01 -> 01.25 처럼 순서 변경
                            # parts[0]: 일, parts[1]: 월
                            date_val = f"{parts[1]}.{parts[0]}"
                            
                    home_text = cells[2].inner_text().strip()
                    away_text = cells[4].inner_text().strip()
                    
                    home_team, home_rank = DataProcessor.parse_team_rank(home_text)
                    away_team, away_rank = DataProcessor.parse_team_rank(away_text)
                    
                    if home_team.isdigit(): continue # 헤더 행 스킵
                    
                    data_list.append({
                        "Round": round_num,
                        "Company": comp_name,
                        "날짜": date_val,
                        "시간": date_raw[1].strip() if len(date_raw) > 1 else '',
                        "홈": home_team,
                        "홈순위": home_rank,
                        "스코어": cells[3].inner_text().strip(),
                        "원정": away_team,
                        "원정순위": away_rank,
                        "승": cells[5].inner_text().strip() if len(cells) > 5 else "-",
                        "무": cells[6].inner_text().strip() if len(cells) > 6 else "-",
                        "패": cells[7].inner_text().strip() if len(cells) > 7 else "-"
                    })
                    count += 1
                except: continue
        except Exception as e:
            self.log(f"{comp_name} 처리 중 에러: {e}")

