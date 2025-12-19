from PyQt5.QtCore import QThread, pyqtSignal
from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor

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

