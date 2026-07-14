from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from gui.widgets.league_widget import LeagueCrawlWidget


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("스코어 크롤링 프로그램")
        self.setGeometry(100, 100, 900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.league_page = LeagueCrawlWidget()
        layout.addWidget(self.league_page)

