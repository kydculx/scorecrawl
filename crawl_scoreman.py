import sys
import subprocess
import os
import re
import json
import logging
from datetime import datetime

# ==========================================
# 패키지 자동 설치 및 확인 (최상단 유지)
# ==========================================
def check_and_install_packages():
    """필요한 패키지가 설치되어 있는지 확인하고 없으면 설치"""
    required_packages = {
        'pandas': 'pandas',
        'PyQt5': 'PyQt5',
        'playwright': 'playwright',
        'openpyxl': 'openpyxl'
    }
    
    missing_packages = []
    
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("필요한 패키지가 설치되지 않았습니다. 자동으로 설치합니다...")
        print(f"설치할 패키지: {', '.join(missing_packages)}")
        
        # requirements.txt가 있으면 사용, 없으면 개별 설치
        requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        if os.path.exists(requirements_file):
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
                print("패키지 설치가 완료되었습니다.")
            except subprocess.CalledProcessError:
                print("패키지 설치 중 오류가 발생했습니다. 수동으로 설치해주세요:")
                print(f"pip install -r requirements.txt")
                sys.exit(1)
        else:
            try:
                for package in missing_packages:
                    print(f"{package} 설치 중...")
                    subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print("패키지 설치가 완료되었습니다.")
            except subprocess.CalledProcessError:
                print("패키지 설치 중 오류가 발생했습니다. 수동으로 설치해주세요:")
                print(f"pip install {' '.join(missing_packages)}")
                sys.exit(1)
        
        # playwright의 경우 브라우저도 설치 필요
        try:
            import playwright
            print("Playwright 브라우저 설치 중...")
            subprocess.check_call([sys.executable, '-m', 'playwright', 'install', 'chromium'])
        except:
            pass

# 패키지 확인 및 설치 실행
check_and_install_packages()

# ==========================================
# 메인 로직 임포트
# ==========================================
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTextEdit, QMessageBox, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from playwright.sync_api import sync_playwright

# ==========================================
# 데이터 처리 클래스
# ==========================================
class DataProcessor:
    @staticmethod
    def clean_team_name(text):
        """팀 이름 정제"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'^\d+\s*', '', text)
        text = re.sub(r'\s*\d+$', '', text)
        return text.strip()

    @staticmethod
    def parse_team_rank(text):
        """팀 이름과 순위 분리"""
        text = re.sub(r'<[^>]+>', '', text)
        bracket_match = re.search(r'\[([^\]]+)\]', text)
        rank = "-"
        
        if bracket_match:
            bracket_content = bracket_match.group(1).strip()
            if bracket_content.isdigit():
                rank = bracket_content
        
        cleaned_text = re.sub(r'\[[^\]]*\]', '', text)
        cleaned_text = re.sub(r'^\d+\s*', '', cleaned_text)
        cleaned_text = re.sub(r'\s*\d+$', '', cleaned_text)
        return cleaned_text.strip(), rank

    @staticmethod
    def safe_get_value(val):
        """값 안전하게 추출"""
        try:
            if isinstance(val, pd.Series):
                val = val.iloc[0] if not val.empty else None
            if val is None:
                return None
            if isinstance(val, float) and (val != val):  # NaN check
                return None
            return val
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def safe_excel_value(val):
        """엑셀 저장용 값 변환"""
        if val is None: return ""
        try:
            if isinstance(val, float) and (val != val): return ""
        except: pass
        if val == "": return ""
        if isinstance(val, (int, float)): return str(val)
        try:
            return ''.join(char for char in str(val).strip() if ord(char) >= 32 or char in '\n\r\t')
        except: return ""

    @classmethod
    def save_results(cls, df, title, ordered_companies, log_callback=None):
        if df.empty:
            if log_callback: log_callback("데이터가 없습니다.")
            return None

        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        filename = f"{safe_title}.xlsx"
        json_filename = f"{safe_title}.json"

        if log_callback: log_callback("\n[데이터 변환 및 저장 중...]")

        # 1. 데이터 프레임 전처리 (피벗)
        index_cols = ["Round", "날짜", "시간", "홈", "홈순위", "스코어", "원정", "원정순위"]
        df_unique = df.drop_duplicates(subset=index_cols + ["Company"])
        pivot_df = df_unique.pivot(index=index_cols, columns="Company", values=["승", "무", "패"])
        pivot_df = pivot_df.swaplevel(0, 1, axis=1)
        
        # 컬럼 정렬
        sorted_cols = []
        for comp in ordered_companies:
            for type_ in ["승", "무", "패"]:
                if (comp, type_) in pivot_df.columns:
                    sorted_cols.append((comp, type_))
        pivot_df = pivot_df.reindex(columns=sorted_cols)
        pivot_df.reset_index(inplace=True)

        # 행 정렬
        pivot_df['_라운드_정렬'] = pd.to_numeric(pivot_df['Round'], errors='coerce')
        pivot_df['_날짜_정렬'] = pivot_df['날짜'].apply(
            lambda x: pd.to_datetime(x, format='%m.%d', errors='coerce') if pd.notna(x) else pd.NaT
        )
        pivot_df = pivot_df.sort_values(by=['_라운드_정렬', '_날짜_정렬', '시간'], na_position='last')
        pivot_df.drop(columns=['_라운드_정렬', '_날짜_정렬'], inplace=True)
        pivot_df.reset_index(drop=True, inplace=True)
        pivot_df.index.name = "순서"

        if log_callback: log_callback(f"[결과] 총 {len(pivot_df)}개의 경기 데이터 처리")

        # 2. JSON 생성 및 저장
        json_data = cls._create_json_data(pivot_df, index_cols)
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        if log_callback: log_callback(f"JSON 저장 완료: {json_filename}")

        # 3. Excel 생성
        # 실제 데이터에 존재하는 회사 목록 업데이트
        companies_in_data = set()
        for match in json_data:
            for comp in match.get("배당", {}).keys():
                companies_in_data.add(comp)
        
        final_companies = [c for c in ordered_companies if c in companies_in_data]
        for c in companies_in_data:
            if c not in final_companies:
                final_companies.append(c)

        cls._create_excel(json_data, filename, final_companies)
        if log_callback: log_callback(f"엑셀 저장 완료: {filename}")

        return filename

    @classmethod
    def _create_json_data(cls, df, match_info_cols):
        json_data = []
        for _, row in df.iterrows():
            match_data = {}
            
            # 기본 정보
            if "Round" in df.columns: match_data["Round"] = cls.safe_get_value(row["Round"])
            
            date_val = cls.safe_get_value(row["날짜"]) if "날짜" in df.columns else None
            time_val = cls.safe_get_value(row["시간"]) if "시간" in df.columns else None
            if date_val or time_val:
                match_data["경기일시"] = {"날짜": date_val, "시간": time_val}

            # 팀 정보
            for side in ["홈", "원정"]:
                team = cls.safe_get_value(row[side]) if side in df.columns else None
                rank = cls.safe_get_value(row[f"{side}순위"]) if f"{side}순위" in df.columns else None
                if team or rank:
                    match_data[side] = {"팀": team, "순위": rank}

            # 스코어
            score = cls.safe_get_value(row["스코어"]) if "스코어" in df.columns else "-"
            score = str(score).strip() if score else "-"
            if ":" in score:
                p = score.split(":")
                match_data["스코어"] = f"{p[0].strip()}-{p[1].strip()}"
            elif "-" not in score and score != "-":
                 match_data["스코어"] = score
            else:
                 match_data["스코어"] = score

            # 배당 정보
            odds_data = {}
            for col in df.columns:
                if isinstance(col, tuple) and len(col) == 2:
                    comp, type_ = col
                    if comp not in match_info_cols and type_ in ["승", "무", "패"]:
                        if comp not in odds_data: odds_data[comp] = {}
                        odds_data[comp][type_] = cls.safe_get_value(row[col])
            
            if odds_data: match_data["배당"] = odds_data
            
            # 유효성 검사 (팀 정보 없음 제외)
            if not match_data.get("홈", {}).get("팀") and not match_data.get("원정", {}).get("팀"):
                continue
                
            json_data.append(match_data)
        return json_data

    @classmethod
    def _create_excel(cls, json_data, filename, companies):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font
            
            wb = Workbook()
            ws = wb.active
            
            # 스타일
            align_center = Alignment(horizontal='center', vertical='center')
            font_bold = Font(bold=True)
            
            # 헤더 구성
            row1, row2 = [], []
            
            # 고정 헤더
            headers = [("Round", 1), ("경기일시", 2, ["날짜", "시간"]), 
                       ("홈", 2, ["팀", "순위"]), ("스코어", 1), ("원정", 2, ["팀", "순위"])]
            
            for h in headers:
                if len(h) == 2: # 단일 컬럼
                    row1.append(h[0])
                    row2.append("")
                else: # 그룹 컬럼
                    row1.append(h[0])
                    row1.extend([""] * (h[1]-1))
                    row2.extend(h[2])

            # 배당 회사 헤더
            for comp in companies:
                row1.append(comp)
                row1.extend(["", ""])
                row2.extend(["승", "무", "패"])

            ws.append(row1)
            ws.append(row2)

            # 헤더 스타일 및 병합
            for row in ws.iter_rows(min_row=1, max_row=2):
                for cell in row:
                    cell.alignment = align_center
                    cell.font = font_bold
            
            # 병합 로직
            curr_col = 1
            # Round
            ws.merge_cells(start_row=1, start_column=curr_col, end_row=2, end_column=curr_col)
            curr_col += 1
            # 경기일시
            ws.merge_cells(start_row=1, start_column=curr_col, end_row=1, end_column=curr_col+1)
            curr_col += 2
            # 홈
            ws.merge_cells(start_row=1, start_column=curr_col, end_row=1, end_column=curr_col+1)
            curr_col += 2
            # 스코어
            ws.merge_cells(start_row=1, start_column=curr_col, end_row=2, end_column=curr_col)
            curr_col += 1
            # 원정
            ws.merge_cells(start_row=1, start_column=curr_col, end_row=1, end_column=curr_col+1)
            curr_col += 2
            
            # 배당 회사들
            for _ in companies:
                ws.merge_cells(start_row=1, start_column=curr_col, end_row=1, end_column=curr_col+2)
                curr_col += 3
            
            # 데이터 채우기
            for match in json_data:
                row = []
                row.append(cls.safe_excel_value(match.get("Round")))
                
                dt = match.get("경기일시", {})
                row.extend([cls.safe_excel_value(dt.get("날짜")), cls.safe_excel_value(dt.get("시간"))])
                
                home = match.get("홈", {})
                row.extend([cls.safe_excel_value(home.get("팀")), cls.safe_excel_value(home.get("순위"))])
                
                row.append(cls.safe_excel_value(match.get("스코어")))
                
                away = match.get("원정", {})
                row.extend([cls.safe_excel_value(away.get("팀")), cls.safe_excel_value(away.get("순위"))])
                
                odds = match.get("배당", {})
                for comp in companies:
                    c_odds = odds.get(comp, {})
                    row.extend([
                        cls.safe_excel_value(c_odds.get("승")),
                        cls.safe_excel_value(c_odds.get("무")),
                        cls.safe_excel_value(c_odds.get("패"))
                    ])
                ws.append(row)

            # 전체 데이터 정렬
            for row in ws.iter_rows(min_row=3, max_row=ws.max_row):
                for cell in row:
                    cell.alignment = align_center

            wb.save(filename)
            
        except Exception as e:
            raise Exception(f"Excel 생성 실패: {str(e)}")

# ==========================================
# 크롤러 클래스
# ==========================================
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

# ==========================================
# GUI 클래스
# ==========================================
class CrawlThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, url, max_rounds=None):
        super().__init__()
        self.url = url
        self.max_rounds = max_rounds
        self.crawler = None
        self.is_running = True
    
    def run(self):
        try:
            self.crawler = ScoreCrawler(self.log_signal.emit)
            df, title, companies = self.crawler.crawl(self.url, self.max_rounds)
            
            if not self.is_running:
                self.finished_signal.emit(False, "중지됨")
                return
                
            filename = DataProcessor.save_results(df, title, companies, self.log_signal.emit)
            if filename:
                self.finished_signal.emit(True, filename)
            else:
                self.finished_signal.emit(False, "데이터 없음")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def stop(self):
        self.is_running = False
        self.log_signal.emit("중지 요청...")

class ScoreCrawlGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("스코어 크롤링 프로그램 v2.0")
        self.setGeometry(100, 100, 800, 600)
        
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        
        # 도메인 & 리그
        top_layout = QHBoxLayout()
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["scoreman123.com", "nowgoal.com"])
        self.domain_combo.currentIndexChanged.connect(self.update_league_list)
        
        self.league_combo = QComboBox()
        self.league_combo.currentIndexChanged.connect(self.update_url)
        
        top_layout.addWidget(QLabel("도메인:"))
        top_layout.addWidget(self.domain_combo)
        top_layout.addWidget(QLabel("리그:"))
        top_layout.addWidget(self.league_combo, 1)
        layout.addLayout(top_layout)
        
        # URL
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        url_layout.addWidget(QLabel("URL:"))
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 옵션
        opt_layout = QHBoxLayout()
        self.max_rounds = QLineEdit()
        self.max_rounds.setPlaceholderText("전체")
        opt_layout.addWidget(QLabel("최대 라운드:"))
        opt_layout.addWidget(self.max_rounds)
        layout.addLayout(opt_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("시작")
        self.btn_start.clicked.connect(self.start)
        self.btn_stop = QPushButton("중지")
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)
        
        # 로그
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        
        self.init_data()

    def init_data(self):
        self.league_paths = [
            ("리그 선택", ""),
            ("K리그 1", "/subleague/15"),
            ("K리그 2", "/subleague/1292"),
            ("호주 A-리그", "/subleague/273"),
            ("프리미어리그", "/league/36"),
            ("세리에 A", "/league/34"),
            ("라리가", "/league/31"),
            ("분데스리가", "/league/8"),
            ("리그 1", "/league/11"),
            ("챔피언스리그", "/cupmatch/103"),
            ("유로파리그", "/cupmatch/113"),
            ("유로파 컨퍼런스리그", "/cupmatch/2187"),
            ("일본 J1리그", "/subleague/25"),
            ("메이저 리그 사커", "/subleague/21"),
            ("CONCACAF챔피언스컵", "/cupmatch/344"),
            ("AFC 아시안컵", "/cupmatch/95"),
        ]
        self.update_league_list()

    def update_league_list(self):
        self.league_combo.blockSignals(True)
        self.league_combo.clear()
        domain = self.domain_combo.currentText()
        
        for name, path in self.league_paths:
            url = f"https://football.{domain}{path}" if path else ""
            self.league_combo.addItem(name, url)
            
        self.league_combo.blockSignals(False)
        self.update_url()

    def update_url(self):
        url = self.league_combo.currentData()
        if not url:
            domain = self.domain_combo.currentText()
            url = f"https://{domain}"
        self.url_input.setText(url)

    def log(self, msg):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start(self):
        url = self.url_input.text().strip()
        if not url: return
        
        rounds = None
        if self.max_rounds.text().strip():
            try: rounds = int(self.max_rounds.text())
            except: pass
            
        self.thread = CrawlThread(url, rounds)
        self.thread.log_signal.connect(self.log)
        self.thread.finished_signal.connect(self.finished)
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_view.clear()
        self.thread.start()

    def stop(self):
        if self.thread: self.thread.stop()

    def finished(self, success, msg):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if success:
            QMessageBox.information(self, "완료", f"저장 완료:\n{msg}")
        else:
            if msg != "중지됨":
                QMessageBox.critical(self, "오류", msg)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScoreCrawlGUI()
    window.show()
    sys.exit(app.exec_())
