@echo off
cd /d %~dp0
call venv\Scripts\activate.bat
python crawl_scoreman.py
pause

