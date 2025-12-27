from PyQt5.QtCore import QThread, pyqtSignal
from crawler.score_crawler import ScoreCrawler
from crawler.data_processor import DataProcessor

class CrawlThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, url, max_rounds=None, league_name=None, season_name=None):
        super().__init__()
        self.url = url
        self.max_rounds = max_rounds
        self.league_name = league_name
        self.season_name = season_name
        self.crawler = None
        self.is_running = True
    
    def run(self):
        try:
            self.crawler = ScoreCrawler(self.log_signal.emit)
            df, title, companies = self.crawler.crawl(self.url, self.max_rounds)
            
            if not self.is_running:
                self.finished_signal.emit(False, "중지됨")
                return
                
            # 파일명 생성: "{리그명}_{시즌명}"
            if self.league_name and self.season_name:
                custom_title = f"{self.league_name}_{self.season_name}"
            else:
                custom_title = title

            filename = DataProcessor.save_results(df, custom_title, companies, self.log_signal.emit)
            if filename:
                self.finished_signal.emit(True, filename)
            else:
                self.finished_signal.emit(False, "데이터 없음")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def stop(self):
        self.is_running = False
        self.log_signal.emit("중지 요청...")

