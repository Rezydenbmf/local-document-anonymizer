@echo off
REM Ten skrypt pokazuje konsole - przydatne do debugowania. Do
REM codziennego uzytku bez widocznego okienka konsoli uzyj uruchom.vbs.
cd /d "%~dp0"
".venv\Scripts\python.exe" src\main.py
if errorlevel 1 (
    echo.
    echo Aplikacja zakonczyla sie bledem - zobacz komunikat powyzej.
    pause
)
