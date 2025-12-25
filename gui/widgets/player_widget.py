from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QComboBox, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal
from utils.constants import LEAGUE_DATA, TEAM_PLAYER_URLS
from crawler.player_crawler import PlayerCrawler
from crawler.data_processor import DataProcessor
from gui.widgets.team_widget import TeamFetcherThread

class PlayerFetcherThread(QThread):
    finished_signal = pyqtSignal(list)
    log_signal = pyqtSignal(str)
    
    def __init__(self, player_list_url, team_name=None):
        super().__init__()
        self.player_list_url = player_list_url
        self.team_name = team_name
        
    def run(self):
        crawler = PlayerCrawler(self.log_signal.emit)
        players = crawler.get_players(self.player_list_url, self.team_name)
        self.finished_signal.emit(players)

class PlayerDataCrawlThread(QThread):
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)
    
    def __init__(self, player_url, player_name, summary_stats=None):
        super().__init__()
        self.player_url = player_url
        self.player_name = player_name
        self.summary_stats = summary_stats
        self.is_running = True
        
    def run(self):
        try:
            crawler = PlayerCrawler(self.log_signal.emit)
            result_data = crawler.crawl_player_data(self.player_url, self.player_name, self.summary_stats)
            
            if not self.is_running:
                self.finished_signal.emit(False, "중지됨")
                return
            
            filename = DataProcessor.save_player_results(result_data, self.player_name, self.log_signal.emit)
            if filename:
                self.finished_signal.emit(True, filename)
            else:
                self.finished_signal.emit(False, "데이터 없음")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def stop(self):
        self.is_running = False

class PlayerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. 도메인 & 리그 선택
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

        self.season_combo = QComboBox()
        self.season_combo.currentIndexChanged.connect(self.on_season_changed)
        
        top_layout.addWidget(QLabel("시즌:"))
        top_layout.addWidget(self.season_combo)
        
        layout.addLayout(top_layout)
        
        # 2. 팀 & 선수 선택
        selection_layout = QHBoxLayout()
        
        self.team_combo = QComboBox()
        self.team_combo.currentIndexChanged.connect(self.on_team_changed)
        
        self.player_combo = QComboBox()
        self.player_combo.currentIndexChanged.connect(self.on_player_changed)
        
        selection_layout.addWidget(QLabel("팀:"))
        selection_layout.addWidget(self.team_combo, 1)
        selection_layout.addWidget(QLabel("선수:"))
        selection_layout.addWidget(self.player_combo, 1)
        
        layout.addLayout(selection_layout)
        
        # 버튼
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("크롤링 시작")
        self.btn_start.clicked.connect(self.start_crawl)
        self.btn_start.setEnabled(False)
        
        btn_layout.addWidget(self.btn_start)
        layout.addLayout(btn_layout)
        
        # 로그
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)
        
        # 초기화
        self.init_league_data()
        self.fetch_team_thread = None
        self.fetch_player_thread = None
        self.crawl_thread = None

    def init_league_data(self):
        self.league_combo.addItem("리그를 선택하세요", {})
        # LEAGUE_DATA 구조: {name, seasons: [(name, league_url, team_url), ...]}
        for league_data in LEAGUE_DATA:
            name = league_data["name"]
            self.league_combo.addItem(name, league_data)
        
    def update_league_urls(self):
        self.on_season_changed(self.season_combo.currentIndex())

    def on_league_changed(self, index):
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        
        league_data = self.league_combo.currentData()
        if league_data and "seasons" in league_data:
            for season_info in league_data["seasons"]:
                season_name = season_info[0]
                team_list_path = season_info[2]
                self.season_combo.addItem(season_name, team_list_path)
                
        self.season_combo.blockSignals(False)
        self.on_season_changed(self.season_combo.currentIndex())
        
    def on_season_changed(self, index):
        team_path = self.season_combo.currentData()
        self.team_combo.clear()
        self.player_combo.clear()
        self.btn_start.setEnabled(False)
        
        if team_path:
            domain = self.domain_combo.currentText()
            url = f"https://football.{domain}{team_path}"
            
            self.log(f"시즌 선택됨: {self.season_combo.currentText()}. 팀 목록을 가져옵니다.")
            self.fetch_teams(url)
        
    def fetch_teams(self, url):
        self.log(f"팀 목록 가져오기... ({url})")
        
        self.fetch_team_thread = TeamFetcherThread(url)
        self.fetch_team_thread.log_signal.connect(self.log)
        self.fetch_team_thread.finished_signal.connect(self.on_teams_fetched)
        self.fetch_team_thread.start()
        
    def on_teams_fetched(self, teams):
        self.team_combo.clear()
        if not teams:
            self.log("팀을 찾을 수 없습니다.")
            return
            
        self.log(f"{len(teams)}개의 팀을 가져왔습니다.")
        self.team_combo.addItem("팀을 선택하세요", "")
        for team in teams:
            self.team_combo.addItem(team['name'], team['url'])

    def on_team_changed(self, index):
        # 팀이 선택되면, TEAM_PLAYER_URLS에서 해당 팀의 선수 목록 URL을 조회
        team_url = self.team_combo.currentData()
        team_name = self.team_combo.currentText()
        
        self.player_combo.clear()
        self.btn_start.setEnabled(False)
        
        if team_url and team_name:
            # TEAM_PLAYER_URLS에서 선수 URL 가져오기
            player_path = TEAM_PLAYER_URLS.get(team_name)
            
            if not player_path:
                self.log(f"'{team_name}'의 선수 데이터 URL이 등록되지 않았습니다. (utils/constants.py 확인)")
                return

            domain = self.domain_combo.currentText()
            url = f"https://football.{domain}{player_path}"
            
            self.log(f"선수 목록 가져오기... (팀: {team_name}, URL: {url})")
            
            self.fetch_player_thread = PlayerFetcherThread(url, team_name)
            self.fetch_player_thread.log_signal.connect(self.log)
            self.fetch_player_thread.finished_signal.connect(self.on_players_fetched)
            self.fetch_player_thread.start()

    def on_players_fetched(self, players):
        self.player_combo.clear()
        if not players:
            self.log("선수를 찾을 수 없습니다.")
            return
            
        self.log(f"{len(players)}명의 선수를 가져왔습니다.")
        self.player_combo.addItem("선수를 선택하세요", "")
        for player in players:
            # player 객체를 itemData로 저장 (stats 포함)
            self.player_combo.addItem(player['name'], player)

    def on_player_changed(self, index):
        player_data = self.player_combo.currentData()
        if player_data and isinstance(player_data, dict) and player_data.get("url"):
            self.btn_start.setEnabled(True)
        else:
            self.btn_start.setEnabled(False)

    def start_crawl(self):
        player_data = self.player_combo.currentData()
        if not player_data: return
        
        player_name = player_data["name"]
        
        # URL 처리
        path = player_data["url"]
        domain = self.domain_combo.currentText()
        if path.startswith("http"):
            url = path
        else:
            url = f"https://football.{domain}{path}"
        
        # 요약 통계 추출
        summary_stats = player_data.get("summary_stats")
        
        self.log(f"크롤링 시작: {player_name} ({url})")
        
        self.btn_start.setEnabled(False)
        self.crawl_thread = PlayerDataCrawlThread(url, player_name, summary_stats)
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

    def log(self, msg):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())
