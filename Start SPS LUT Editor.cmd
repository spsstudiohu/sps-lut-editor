@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
set "PYTHONUTF8=1"
cd /d "%~dp0"
title SPS LUT Editor

if not exist ".venv\Scripts\python.exe" (
    echo First start: preparing the Python environment...
    set "PYTHON_CMD="
    if exist "%LOCALAPPDATA%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "PYTHON_CMD=%LOCALAPPDATA%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if not defined PYTHON_CMD (
        where py >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=py -3"
    )
    if not defined PYTHON_CMD (
        where python >nul 2>nul
        if not errorlevel 1 set "PYTHON_CMD=python"
    )
    if not defined PYTHON_CMD goto :no_python
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 goto :error
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r "source\requirements.txt"
    if errorlevel 1 goto :error
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" /b ".venv\Scripts\pythonw.exe" "source\main.py"
) else (
    ".venv\Scripts\python.exe" "source\main.py"
)
exit /b 0

:error
echo.
echo SPS LUT Editor could not be started.
echo Check your internet connection during the first installation, then try again.
pause
exit /b 1

:no_python
echo.
echo Python 3 was not found on this computer.
echo Install Python 3 from https://www.python.org/downloads/windows/ and start this file again.
pause
exit /b 1
