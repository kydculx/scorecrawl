from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QTextEdit, QMessageBox,
                             QComboBox, QCheckBox)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from ..workers import CrawlThread, AllSeasonCrawlThread
from utils.constants import LEAGUE_DATA
from crawler.season_fetcher import fetch_seasons


class SeasonFetchThread(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, league_url, domain):
        super().__init__()
        self.league_url = league_url
        self.domain = domain

    def run(self):
        try:
            seasons = fetch_seasons(self.league_url, self.domain)
            self.finished.emit(seasons)
        except Exception as e:
            self.error.emit(str(e))


class LeagueCrawlWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.season_fetch_thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        self.domain_combo = QComboBox()
        self.domain_combo.addItems(["scoreman123.com", "nowgoal.com"])
        self.domain_combo.currentIndexChanged.connect(self.on_domain_or_league_changed)

        self.league_combo = QComboBox()
        self.league_combo.currentIndexChanged.connect(self.on_domain_or_league_changed)

        self.season_combo = QComboBox()
        self.season_combo.currentIndexChanged.connect(self.update_url)

        self.check_all = QCheckBox("전체")
        self.check_all.stateChanged.connect(self.on_all_check_changed)

        top_layout.addWidget(QLabel("도메인:"))
        top_layout.addWidget(self.domain_combo)
        top_layout.addWidget(QLabel("리그:"))
        top_layout.addWidget(self.league_combo, 1)
        top_layout.addWidget(QLabel("시즌:"))
        top_layout.addWidget(self.season_combo)
        top_layout.addWidget(self.check_all)
        layout.addLayout(top_layout)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setReadOnly(True)
        url_layout.addWidget(QLabel("URL:"))
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)

        opt_layout = QHBoxLayout()
        self.max_rounds = QLineEdit()
        self.max_rounds.setPlaceholderText("전체")
        opt_layout.addWidget(QLabel("최대 라운드:"))
        opt_layout.addWidget(self.max_rounds)
        layout.addLayout(opt_layout)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("시작")
        self.btn_start.clicked.connect(self.start)
        self.btn_stop = QPushButton("중지")
        self.btn_stop.clicked.connect(self.stop)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        layout.addLayout(btn_layout)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view)

        self.update_league_list()

    def update_league_list(self):
        self.league_combo.blockSignals(True)
        self.league_combo.clear()
        self.league_combo.addItem("리그를 선택하세요", {})
        for league_data in LEAGUE_DATA:
            self.league_combo.addItem(league_data["name"], league_data)
        self.league_combo.blockSignals(False)
        self.on_domain_or_league_changed()

    def on_domain_or_league_changed(self):
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        self.season_combo.blockSignals(False)
        self.url_input.clear()

        league_data = self.league_combo.currentData()
        domain = self.domain_combo.currentText()
        if league_data and "url" in league_data:
            self.log(f"시즌 목록 로딩 중...")
            self.season_fetch_thread = SeasonFetchThread(league_data["url"], domain)
            self.season_fetch_thread.finished.connect(self.on_season_result)
            self.season_fetch_thread.error.connect(self.on_season_error)
            self.season_fetch_thread.start()

    def on_season_result(self, seasons):
        self.season_combo.blockSignals(True)
        self.season_combo.clear()
        if seasons:
            for s in seasons:
                self.season_combo.addItem(s["name"], s)
        else:
            self.season_combo.addItem("시즌 없음", None)
        self.season_combo.blockSignals(False)
        self.update_url()

    def on_season_error(self, err_msg):
        self.log(f"시즌 로딩 오류: {err_msg}")

    def on_all_check_changed(self, state):
        checked = state == Qt.Checked
        self.season_combo.setEnabled(not checked)
        if checked:
            self.url_input.setText("전체 시즌 (자동 크롤링)")
        else:
            self.update_url()

    def update_url(self):
        if self.check_all.isChecked():
            self.url_input.setText("전체 시즌 (자동 크롤링)")
            return
        data = self.season_combo.currentData()
        domain = self.domain_combo.currentText()
        if data and isinstance(data, dict) and data.get("url"):
            url = f"https://football.{domain}{data['url']}"
            self.url_input.setText(url)

    def log(self, msg):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def start(self):
        if self.check_all.isChecked():
            self.start_all_seasons()
            return

        url = self.url_input.text().strip()
        league_name = self.league_combo.currentText()
        season_name = self.season_combo.currentText()

        if not url:
            return

        rounds = None
        if self.max_rounds.text().strip():
            try:
                rounds = int(self.max_rounds.text())
            except:
                pass

        self.thread = CrawlThread(url, rounds, league_name, season_name)
        self.thread.log_signal.connect(self.log)
        self.thread.finished_signal.connect(self.finished)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_view.clear()
        self.thread.start()

    def start_all_seasons(self):
        league_name = self.league_combo.currentText()
        domain = self.domain_combo.currentText()

        seasons = []
        for i in range(self.season_combo.count()):
            data = self.season_combo.itemData(i)
            if data and isinstance(data, dict) and data.get("url"):
                seasons.append(data)

        if not seasons:
            QMessageBox.warning(self, "알림", "크롤링할 시즌이 없습니다.")
            return

        rounds = None
        if self.max_rounds.text().strip():
            try:
                rounds = int(self.max_rounds.text())
            except:
                pass

        self.thread = AllSeasonCrawlThread(seasons, domain, league_name, rounds)
        self.thread.log_signal.connect(self.log)
        self.thread.finished_signal.connect(self.finished)

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.log_view.clear()
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()

    def finished(self, success, msg):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if success:
            QMessageBox.information(self, "완료", f"저장 완료:\n{msg}")
        else:
            if msg != "중지됨":
                QMessageBox.critical(self, "오류", msg)
