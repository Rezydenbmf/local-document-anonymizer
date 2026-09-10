@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" src\main.py
if errorlevel 1 (
    echo.
    echo Aplikacja zakonczyla sie bledem - zobacz komunikat powyzej.
    pause
)
