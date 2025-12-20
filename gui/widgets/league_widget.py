from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QTextEdit, QMessageBox, QComboBox)
from ..workers import CrawlThread
from utils.constants import LEAGUE_PATHS

class LeagueCrawlWidget(QWidget):
    """리그 정보를 크롤링하는 화면 위젯"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
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
        
        self.update_league_list()

    def update_league_list(self):
        self.league_combo.blockSignals(True)
        self.league_combo.clear()
        domain = self.domain_combo.currentText()
        
        for item in LEAGUE_PATHS:
            name = item[0]
            path = item[1] if len(item) > 1 else ""
            
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

