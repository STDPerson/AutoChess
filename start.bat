@echo off
cd /d "%~dp0"
echo Mengaktifkan Virtual Environment...
call .\venv\Scripts\activate.bat
echo Menjalankan Bot...
python main.py
pause
