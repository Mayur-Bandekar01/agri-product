@echo off
echo === Starting Adinath Agri Services Backend ===
echo.

cd /d "%~dp0backend"

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Starting backend server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
