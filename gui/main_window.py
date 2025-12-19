from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
from gui.widgets.league_widget import LeagueCrawlWidget
from gui.widgets.team_widget import TeamWidget
from gui.widgets.player_widget import PlayerWidget

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("스코어 크롤링 통합 프로그램")
        self.setGeometry(100, 100, 900, 700)
        
        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 전체 레이아웃 (수직)
        main_layout = QVBoxLayout(main_widget)
        
        # 네비게이션 버튼 레이아웃 (수평)
        nav_layout = QHBoxLayout()
        
        self.btn_league = QPushButton("리그")
        self.btn_team = QPushButton("팀")
        self.btn_player = QPushButton("선수")
        
        # 버튼 스타일 설정 (높이 키우기)
        for btn in [self.btn_league, self.btn_team, self.btn_player]:
            btn.setMinimumHeight(40)
            nav_layout.addWidget(btn)
        
        main_layout.addLayout(nav_layout)
        
        # 스택 위젯 (화면 전환용)
        self.stacked_widget = QStackedWidget()
        
        # 1. 리그 화면
        self.league_page = LeagueCrawlWidget()
        self.stacked_widget.addWidget(self.league_page)
        
        # 2. 팀 화면
        self.team_page = TeamWidget()
        self.stacked_widget.addWidget(self.team_page)
        
        # 3. 선수 화면
        self.player_page = PlayerWidget()
        self.stacked_widget.addWidget(self.player_page)
        
        main_layout.addWidget(self.stacked_widget)
        
        # 버튼 이벤트 연결
        self.btn_league.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.btn_team.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.btn_player.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        
        # 초기 스타일 설정 (리그 버튼 활성화)
        self.update_nav_style(0)
        self.stacked_widget.currentChanged.connect(self.update_nav_style)
        
    def update_nav_style(self, index):
        """현재 선택된 탭 강조"""
        buttons = [self.btn_league, self.btn_team, self.btn_player]
        for i, btn in enumerate(buttons):
            if i == index:
                btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
            else:
                btn.setStyleSheet("")

