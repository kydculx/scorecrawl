import sys
from PyQt5.QtWidgets import QApplication
from utils.package_installer import check_and_install_packages

# 패키지 확인 및 설치 실행 (GUI 로드 전)
check_and_install_packages()

from gui.main_window import MainApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())

