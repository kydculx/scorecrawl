@echo off
chcp 65001 >nul
cd /d %~dp0

REM 가상환경 활성화
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo 가상환경을 찾을 수 없습니다. venv 폴더가 있는지 확인해주세요.
    pause
    exit /b 1
)

echo PyInstaller 설치 확인 중...
python -m pip install --upgrade pyinstaller

if errorlevel 1 (
    echo PyInstaller 설치 실패
    pause
    exit /b 1
)

echo.
echo EXE 파일 빌드 중...
python -m PyInstaller --name="ScoreCrawl" ^
    --onefile ^
    --windowed ^
    --noconsole ^
    --add-data "requirements.txt;." ^
    --hidden-import=PyQt5 ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=playwright ^
    --hidden-import=playwright.sync_api ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.styles ^
    --collect-all playwright ^
    --collect-all PyQt5 ^
    crawl_scoreman.py

if errorlevel 1 (
    echo 빌드 실패
    pause
    exit /b 1
)

echo.
echo 빌드 완료! dist 폴더에 ScoreCrawl.exe 파일이 생성되었습니다.
echo.
pause

