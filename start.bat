@echo off
cd /d "%~dp0"
echo Activating Virtual Environment...
call .\venv\Scripts\activate.bat
echo Starting Bot...
python main.py
pause
