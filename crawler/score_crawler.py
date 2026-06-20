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

    def crawl(self, url, max_rounds=None, default_title="Unknown"):
        data_list = []
        league_title = default_title
        
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
                    # id="title", class="title", class="info_title" 순서로 시도
                    title_element = page.locator("#title")
                    if title_element.count() == 0:
                        title_element = page.locator(".title")
                    if title_element.count() == 0:
                        title_element = page.locator(".info_title")
                    if title_element.count() == 0:
                        title_element = page.locator("title")
                    
                    league_title_full = title_element.inner_text().strip()
                    league_title = league_title_full.split('\n')[0].strip()
                    self.log(f"리그: {league_title}")
                except:
                    self.log(f"리그 제목을 찾을 수 없어 기본값 '{default_title}'을(를) 사용합니다.")

                # 라운드 정보
                try:
                    page.wait_for_selector(".round", timeout=2000)
                except:
                    try:
                        page.wait_for_selector("#Table2", timeout=3000)
                    except:
                        pass

                round_texts = []
                current_round = 38
                
                round_div = page.locator(".round")
                if round_div.count() > 0:
                    round_spans = page.locator(".round span").all()
                    round_texts = [span.get_attribute("round").strip() for span in round_spans if span.get_attribute("round")]
                    if not round_texts:
                        round_texts = [span.inner_text().strip() for span in round_spans if span.inner_text().strip().isdigit()]
                    
                    try:
                        current_el = page.locator(".round span.current").first
                        if current_el.count() == 0:
                            current_el = page.locator(".round span.on").first
                        if current_el.count() > 0:
                            current_round = int(current_el.inner_text().strip())
                    except:
                        pass
                else:
                    try:
                        round_elements = page.locator("#Table2 td[onclick*='changeRound']").all()
                        round_texts = [el.inner_text().strip() for el in round_elements if el.inner_text().strip().isdigit()]
                        current_round_el = page.locator("#Table2 td.round_now").first
                        if current_round_el.count() > 0:
                            current_round = int(current_round_el.inner_text().strip())
                            round_texts.append(str(current_round))
                    except:
                        pass

                round_texts = sorted(list(set(round_texts)), key=int)
                round_texts = [r for r in round_texts if int(r) <= current_round]
                
                if max_rounds:
                    self.log(f"테스트 모드: {max_rounds}개 라운드만 수집")
                    round_texts = round_texts[:max_rounds]

                # 배당 회사 확인
                self.companies = []
                try:
                    if page.locator("#oddsCompany option").first.count() > 0:
                        company_options = page.locator("#oddsCompany option").all()
                        for opt in company_options:
                            val = opt.get_attribute("value")
                            text = opt.inner_text().strip()
                            if val: self.companies.append((val, text))
                except:
                    pass
                
                if not self.companies:
                    self.log("배당 회사 드롭다운이 없습니다. 기본 화면의 승무패 값을 수집합니다.")
                    self.companies = [("", "기본")]
                else:
                    self.log(f"수집 대상 회사: {[n for v, n in self.companies]}")

                # 라운드별 순회
                for round_num in round_texts:
                    self.log(f"\n[{round_num} 라운드] 수집 시작")
                    try:
                        round_btn = page.locator(f".round span[round='{round_num}']").first
                        if round_btn.count() == 0:
                            round_btn = page.locator(".round span").filter(has_text=re.compile(rf"^\s*{round_num}\s*$")).first
                        if round_btn.count() == 0:
                            round_btn = page.locator("#Table2 td").filter(has_text=re.compile(rf"^\s*{round_num}\s*$")).first
                        
                        round_btn.click()
                        page.wait_for_timeout(1000)
                        
                        # 해당 라운드의 순위 정보 수집
                        round_rankings = {}
                        try:
                            # '전반' 탭 클릭하여 전반전 기준 순위표 활성화
                            try:
                                first_half_tab = page.locator("span").filter(has_text=re.compile(r"^전반$")).first
                                if first_half_tab.count() > 0:
                                    first_half_tab.click(force=True)
                                    page.wait_for_timeout(300)
                            except Exception as tab_err:
                                self.log(f"'전반' 탭 클릭 실패: {tab_err}")
                            
                            # standingBox 내의 해당 라운드 li 요소를 JS로 직접 클릭
                            standing_li_selector = f"#standingBox li[data-st-r='{round_num}']"
                            if page.locator(standing_li_selector).count() > 0:
                                prev_text = page.locator("#standingBox").inner_text().strip().replace('\n', ' ')
                                page.eval_on_selector(standing_li_selector, "el => el.click()")
                                
                                # 드롭다운 텍스트 업데이트 대기
                                try:
                                    page.wait_for_function(
                                        f"document.querySelector('#standingBox').innerText.includes('라운드{round_num}')",
                                        timeout=2000
                                    )
                                except:
                                    pass
                                
                                page.wait_for_timeout(1000)
                                curr_text = page.locator("#standingBox").inner_text().strip().replace('\n', ' ')
                                self.log(f"  [순위 드롭다운] {prev_text} -> {curr_text} 변경 완료")
                            
                            # 1. 새로운 List 구조 (#standingList li) 파싱 시도
                            standing_rows = page.locator("#standingList li").all()
                            for row in standing_rows:
                                try:
                                    class_name = row.get_attribute("class") or ""
                                    if "title" in class_name:
                                        continue
                                    
                                    rank_el = row.locator("span.rank")
                                    team_el = row.locator("span.team span.name")
                                    if rank_el.count() > 0 and team_el.count() > 0:
                                        rank_val = rank_el.inner_text().strip()
                                        team_name = team_el.inner_text().strip()
                                        cleaned_name = DataProcessor.clean_team_name(team_name)
                                        if cleaned_name and rank_val.isdigit():
                                            round_rankings[cleaned_name] = rank_val
                                except:
                                    continue
                            
                            # 2. 새로운 구조에서 수집되지 않은 경우 기존 Table 구조 파싱 시도 (Fallback)
                            if not round_rankings:
                                standing_rows = page.locator(".lei_table tr, #Table3 tr, #div_standing tr, #standingBox ~ table tr, #standingBox ~ div table tr").all()
                                for row in standing_rows:
                                    try:
                                        cells = row.locator("td").all()
                                        if len(cells) >= 2:
                                            rank_text = cells[0].inner_text().strip()
                                            if rank_text.isdigit():
                                                rank_val = rank_text
                                                team_span = row.locator(".team span, td a, .team").first
                                                if team_span.count() > 0:
                                                    team_name = team_span.inner_text().strip()
                                                else:
                                                    team_name = cells[1].inner_text().strip()
                                                
                                                cleaned_name = DataProcessor.clean_team_name(team_name)
                                                if cleaned_name:
                                                    round_rankings[cleaned_name] = rank_val
                                    except:
                                        continue
                        except Exception as re_err:
                            self.log(f"라운드 {round_num} 순위표 파싱 에러: {re_err}")
                        
                        if round_rankings:
                            sorted_rankings = sorted(round_rankings.items(), key=lambda x: int(x[1]) if x[1].isdigit() else 999)
                            rankings_str = ", ".join([f"{rank}위:{team}" for team, rank in sorted_rankings])
                            self.log(f"라운드 {round_num} (전반전 기준) 순위 데이터 수집 완료:\n  -> {rankings_str}")
                        
                        for comp_val, comp_name in self.companies:
                            self._process_company_round(page, round_num, comp_val, comp_name, data_list, is_nowgoal, round_rankings)
                            
                    except Exception as e:
                        self.log(f"라운드 {round_num} 에러: {e}")

            except Exception as e:
                self.log(f"크롤링 치명적 오류: {e}")
            finally:
                browser.close()

        return pd.DataFrame(data_list), league_title, [n for v, n in self.companies]

    def _find_team_rank(self, team_name, rankings):
        if not rankings:
            return "-"
        
        # 1. 완전 일치
        cleaned_target = DataProcessor.clean_team_name(team_name)
        if cleaned_target in rankings:
            return rankings[cleaned_target]
            
        # 2. 부분 일치 (예: '인천'이 '인천 유나이티드'에 포함되거나 반대)
        for rank_team, rank_val in rankings.items():
            if cleaned_target in rank_team or rank_team in cleaned_target:
                return rank_val
                
        # 3. 특수문자 및 공백 제거 후 비교 (예: 'FC서울' vs '서울')
        stripped_target = re.sub(r'[^a-zA-Z0-9가-힣]', '', cleaned_target)
        for rank_team, rank_val in rankings.items():
            stripped_rank_team = re.sub(r'[^a-zA-Z0-9가-힣]', '', rank_team)
            if stripped_target in stripped_rank_team or stripped_rank_team in stripped_target:
                return rank_val
                
        return "-"

    def _process_company_round(self, page, round_num, comp_val, comp_name, data_list, is_nowgoal=False, round_rankings=None):
        try:
            if comp_val and page.locator("#oddsCompany").count() > 0:
                page.select_option("#oddsCompany", comp_val)
                # 데이터 로딩 및 렌더링을 위해 대기 시간 증가
                page.wait_for_timeout(500)
            
            # .schedulis 또는 tr 요소 대기
            try:
                page.wait_for_selector(".schedulis, tr", timeout=2000)
            except:
                pass
            
            schedulis_elements = page.locator(".schedulis").all()
            self.log(f"{comp_name} - 발견된 매치(.schedulis) 개수: {len(schedulis_elements)}")
            count = 0
            
            if schedulis_elements:
                for match_el in schedulis_elements:
                    try:
                        # 날짜 & 시간 파싱 (예: "02.28 14:00")
                        date_text = match_el.locator(".date").inner_text().strip()
                        date_raw = date_text.split()
                        date_val = date_raw[0].replace('-', '.') if len(date_raw) > 0 else ""
                        time_val = date_raw[1] if len(date_raw) > 1 else ""
                        
                        if is_nowgoal and '.' in date_val:
                            parts = date_val.split('.')
                            if len(parts) >= 2:
                                date_val = f"{parts[1]}.{parts[0]}"
                                
                        home_text = match_el.locator(".home").inner_text().strip()
                        away_text = match_el.locator(".away").inner_text().strip()
                        
                        home_team, home_rank = DataProcessor.parse_team_rank(home_text)
                        away_team, away_rank = DataProcessor.parse_team_rank(away_text)
                        
                        if round_rankings:
                            if home_rank == "-":
                                home_rank = self._find_team_rank(home_team, round_rankings)
                            if away_rank == "-":
                                away_rank = self._find_team_rank(away_team, round_rankings)
                                
                        score_val = match_el.locator(".score").inner_text().strip()
                        
                        odds_spans = match_el.locator(".odds span").all()
                        win_odds = odds_spans[0].inner_text().strip() if len(odds_spans) > 0 else "-"
                        draw_odds = odds_spans[1].inner_text().strip() if len(odds_spans) > 1 else "-"
                        lose_odds = odds_spans[2].inner_text().strip() if len(odds_spans) > 2 else "-"
                        
                        data_list.append({
                            "Round": round_num,
                            "Company": comp_name,
                            "날짜": date_val,
                            "시간": time_val,
                            "홈": home_team,
                            "홈순위": home_rank,
                            "스코어": score_val,
                            "원정": away_team,
                            "원정순위": away_rank,
                            "승": win_odds,
                            "무": draw_odds,
                            "패": lose_odds
                        })
                        self.log(f"  [수집] {date_val} {time_val} - {home_team}({home_rank}) {score_val} {away_team}({away_rank}) | 배당: {win_odds}/{draw_odds}/{lose_odds}")
                        count += 1
                    except Exception as ex:
                        self.log(f"  [에러] 매치 개별 파싱 실패: {ex}")
                        continue
            else:
                rows = page.locator("tr").all()
                self.log(f"{comp_name} - 발견된 tr 개수: {len(rows)}")
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
                        
                        if round_rankings:
                            if home_rank == "-":
                                home_rank = self._find_team_rank(home_team, round_rankings)
                            if away_rank == "-":
                                away_rank = self._find_team_rank(away_team, round_rankings)
                                
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

