@echo off
title Setup Legal Metrology Compliance System
echo ======================================================================
echo  Installing Legal Metrology Compliance System Environment
echo ======================================================================
cd /d "%~dp0"

echo [*] Creating virtual environment (venv)...
python -m venv venv
if errorlevel 1 (
    echo [!] Standard 'python' command failed. Trying Spyder python runtime...
    "C:\Users\gopal\AppData\Local\spyder-6\python.exe" -m venv venv
)

echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

echo [*] Installing required packages from requirements.txt...
pip install -r requirements.txt

echo [*] Initializing sample demo labels...
python sample_generator.py

echo ======================================================================
echo  Setup Completed Successfully!
echo  Run 'run.bat' to launch the system at http://127.0.0.1:5000
echo ======================================================================
pause
