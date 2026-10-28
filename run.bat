@echo off
title Legal Metrology Compliance System
echo ======================================================================
echo  LEGAL METROLOGY COMPLIANCE VERIFICATION SYSTEM
echo  Packaged Commodities Label Audit Web Application
echo ======================================================================
cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    echo [*] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment not found. Running setup first...
    call setup.bat
)

echo [*] Starting Flask application server...
echo [*] Open your web browser at: http://127.0.0.1:5000
echo ======================================================================
python app.py
pause
