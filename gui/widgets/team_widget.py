from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal
from utils.constants import LEAGUE_PATHS
from crawler.team_crawler import TeamCrawler
from crawler.data_processor import DataProcessor
import re

class TeamFetcherThread(QThread):
    finished_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)
    
    def __init__(self, league_url):
        super().__init__()
        self.league_url = league_url
        
    def run(self):
        crawler = TeamCrawler(self.log_signal.emit)
        teams = crawler.get_teams(self.league_url)
        self.finished_signal.emit(teams)

class TeamDataCrawlThread(QThread):
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)
    
    def __init__(self, team_url, team_name):
        super().__init__()
        self.team_url = team_url
        self.team_name = team_name
        self.is_running = True
        
    def run(self):
        try:
            crawler = TeamCrawler(self.log_signal.emit)
            df = crawler.crawl_team_data(self.team_url, self.team_name)
            
            if not self.is_running:
                self.finished_signal.emit(False, "중지됨")
                return
            
            filename = DataProcessor.save_team_results(df, self.team_name, self.log_signal.emit)
            if filename:
                self.finished_signal.emit(True, filename)
            else:
                self.finished_signal.emit(False, "데이터 없음")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def stop(self):
        self.is_running = False

class TeamWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. 도메인 & 리그 선택 (한 줄로 배치)
        top_layout = QHBoxLayout()
        
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["scoreman123.com", "nowgoal.com"])
        self.domain_combo.currentIndexChanged.connect(self.update_league_urls)
        
        self.league_combo = QComboBox()
        self.league_combo.currentIndexChanged.connect(self.on_league_changed)
        
        top_layout.addWidget(QLabel("도메인:"))
        top_layout.addWidget(self.domain_combo)
        top_layout.addWidget(QLabel("리그:"))
        top_layout.addWidget(self.league_combo, 1)
        
        layout.addLayout(top_layout)
        
        # 2. 팀 선택
        team_layout = QHBoxLayout()
        self.team_combo = QComboBox()
        self.team_combo.currentIndexChanged.connect(self.update_url_input)
        team_layout.addWidget(QLabel("팀:"))
        team_layout.addWidget(self.team_combo, 1)
        layout.addLayout(team_layout)
        
        # URL 입력 (자동완성 되지만 수정 가능)
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        url_layout.addWidget(QLabel("URL:"))
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        # "팀 목록 가져오기" 버튼 제거 (자동화됨)
        
        self.btn_start = QPushButton("크롤링 시작")
        self.btn_start.clicked.connect(self.start_crawl)
        self.btn_start.setEnabled(False) # 팀 선택 전까지 비활성화
        
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)
        
        # 로그
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        
        # 초기화
        self.init_league_data()
        self.crawl_thread = None

    def init_league_data(self):
        # 리그 목록 채우기 (URL은 나중에 도메인에 따라 완성)
        self.league_combo.addItem("리그를 선택하세요", "")
        for item in LEAGUE_PATHS:
            name = item[0]
            # 팀 목록 URL (3번째 요소)
            team_path = item[2] if len(item) > 2 else ""
            
            if team_path: # "리그 선택" 중복 방지
                self.league_combo.addItem(name, team_path)
        
    def update_league_urls(self):
        # 도메인이 바뀌면 현재 선택된 리그의 URL 로직이 바뀔 수 있음
        # 하지만 여기서는 리그 콤보박스의 data 부분에 path만 저장하므로 
        # 실제 URL 생성 시 도메인을 붙이면 됨.
        self.on_league_changed(self.league_combo.currentIndex())

    def on_league_changed(self, index):
        path = self.league_combo.currentData()
        self.team_combo.clear()
        self.btn_start.setEnabled(False)
        self.url_input.clear()
        
        if path:
            self.log(f"리그 선택됨: {self.league_combo.currentText()}. 자동으로 팀 목록을 가져옵니다.")
            self.fetch_teams() # 자동 실행
        
    def fetch_teams(self):
        path = self.league_combo.currentData()
        if not path:
            return
            
        domain = self.domain_combo.currentText()
        url = f"https://football.{domain}{path}"
        
        self.log(f"팀 목록을 가져옵니다... ({url})")
        
        self.fetch_thread = TeamFetcherThread(url)
        self.fetch_thread.log_signal.connect(self.log)
        self.fetch_thread.finished_signal.connect(self.on_teams_fetched)
        self.fetch_thread.start()
        
    def on_teams_fetched(self, teams):
        self.team_combo.clear()
        
        if not teams:
            self.log("팀을 찾을 수 없습니다.")
            return
            
        self.log(f"{len(teams)}개의 팀을 가져왔습니다.")
        self.team_combo.addItem("팀을 선택하세요", "")
        
        for team in teams:
            self.team_combo.addItem(team['name'], team['url'])
            
    def update_url_input(self):
        path = self.team_combo.currentData()
        if path:
            domain = self.domain_combo.currentText()
            
            if path.startswith("http"):
                url = path
            else:
                # 숫자 ID 추출 (가장 마지막에 있는 숫자라고 가정하거나, /team/ 뒤에 있는 숫자 등)
                match = re.search(r'/team/(?:.*/)?(\d+)', path)
                if match:
                    team_id = match.group(1)
                    # summaryleague가 포함된 새로운 경로 생성
                    url = f"https://football.{domain}/team/summaryleague/{team_id}"
                else:
                    # ID 추출 실패 시 기본 동작
                    url = f"https://football.{domain}{path}"
            
            self.url_input.setText(url)
            self.btn_start.setEnabled(True)
        else:
            self.url_input.clear()
            self.btn_start.setEnabled(False)
            
    def log(self, msg):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())
        
    def start_crawl(self):
        url = self.url_input.text()
        team_name = self.team_combo.currentText()
        
        if not url: return
        
        self.log(f"크롤링 시작: {team_name} ({url})")
        
        self.btn_start.setEnabled(False)
        self.crawl_thread = TeamDataCrawlThread(url, team_name)
        self.crawl_thread.log_signal.connect(self.log)
        self.crawl_thread.finished_signal.connect(self.on_crawl_finished)
        self.crawl_thread.start()
        
    def on_crawl_finished(self, success, msg):
        self.btn_start.setEnabled(True)
        if success:
            QMessageBox.information(self, "완료", f"저장 완료:\n{msg}")
        else:
            if msg != "중지됨":
                QMessageBox.critical(self, "오류", msg)
