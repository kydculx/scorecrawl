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
            df, title, _ = self.crawler.crawl(self.url, self.max_rounds, default_title=self.league_name or "Unknown")
            
            if not self.is_running:
                self.finished_signal.emit(False, "중지됨")
                return
                
            # 파일명 생성: "{리그명}_{시즌명}"
            if self.league_name and self.season_name:
                custom_title = f"{self.league_name}_{self.season_name}"
            else:
                custom_title = title

            filename = DataProcessor.save_results(
                df, custom_title, self.log_signal.emit,
                league_name=self.league_name, 
                season_name=self.season_name
            )
            if filename:
                self.finished_signal.emit(True, filename)
            else:
                self.finished_signal.emit(False, "데이터 없음")
                
        except Exception as e:
            self.finished_signal.emit(False, str(e))
            
    def stop(self):
        self.is_running = False
        self.log_signal.emit("중지 요청...")


class AllSeasonCrawlThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(int, int)

    def __init__(self, seasons, domain, league_name, max_rounds=None):
        super().__init__()
        self.seasons = seasons
        self.domain = domain
        self.league_name = league_name
        self.max_rounds = max_rounds
        self.is_running = True

    def run(self):
        total = len(self.seasons)
        completed = 0

        for i, season in enumerate(self.seasons):
            if not self.is_running:
                break

            season_name = season["name"]
            url = f"https://football.{self.domain}{season['url']}"

            self.log_signal.emit(f"\n{'='*50}")
            self.log_signal.emit(f"[{i+1}/{total}] {season_name} 크롤링 시작...")
            self.progress_signal.emit(i + 1, total)

            try:
                crawler = ScoreCrawler(self.log_signal.emit)
                df, title, _ = crawler.crawl(url, self.max_rounds, default_title=self.league_name or "Unknown")

                if not self.is_running:
                    break

                if df.empty:
                    self.log_signal.emit(f"  [건너뜀] {season_name} - 데이터 없음")
                    continue

                custom_title = f"{self.league_name}_{season_name}" if self.league_name and season_name else title

                filename = DataProcessor.save_results(
                    df, custom_title, self.log_signal.emit,
                    league_name=self.league_name,
                    season_name=season_name
                )

                if filename:
                    self.log_signal.emit(f"  [완료] {season_name} → {filename}")
                    completed += 1
                else:
                    self.log_signal.emit(f"  [건너뜀] {season_name} - 데이터 없음")

            except Exception as e:
                self.log_signal.emit(f"  [오류] {season_name} - {e}")
                if not self.is_running:
                    break

        if self.is_running:
            msg = f"전체 {total}개 시즌 중 {completed}개 완료"
            self.log_signal.emit(f"\n{'='*50}")
            self.log_signal.emit(msg)
            self.finished_signal.emit(completed > 0, msg)
        else:
            self.finished_signal.emit(False, "중지됨")

    def stop(self):
        self.is_running = False
        self.log_signal.emit("중지 요청...")

