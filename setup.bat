@echo off
setlocal
title SMHS - Auto Setup
cd /d "%~dp0"

echo ============================================
echo   SMHS project - downloading everything
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Install Python 3.12 or newer from https://www.python.org/downloads/
    echo Tick "Add Python to PATH" during install, then run this file again.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js is not installed.
    echo Install the LTS version from https://nodejs.org/ and run this file again.
    pause
    exit /b 1
)
python --version

echo.
echo [1/6] Creating Python virtual environment...
cd backend
if not exist venv\Scripts\python.exe (
    if exist venv rmdir /s /q venv
    python -m venv venv
    if errorlevel 1 goto :fail
)
call venv\Scripts\activate.bat

echo [2/6] Installing Python packages...
python -m pip install --upgrade pip
pip install --prefer-binary -r requirements.txt
if errorlevel 1 goto :fail

echo [3/6] Setting up local database (SQLite)...
set USE_SQLITE=1
set DJANGO_DEBUG=1
python manage.py migrate --noinput
if errorlevel 1 goto :fail
python manage.py createcachetable
if errorlevel 1 goto :fail
python manage.py seed
if errorlevel 1 goto :fail

echo [4/6] Checking the backend...
python manage.py check
if errorlevel 1 goto :fail
cd ..

echo [5/6] Installing frontend packages (npm)...
cd frontend
call npm install
if errorlevel 1 goto :fail
cd ..

echo [6/6] Creating run.bat...
(
echo @echo off
echo cd /d "%%~dp0"
echo start "SMHS Backend" cmd /k "cd backend && call venv\Scripts\activate.bat && set USE_SQLITE=1&& set DJANGO_DEBUG=1&& python manage.py runserver 8000"
echo start "SMHS Frontend" cmd /k "cd frontend && npm run dev"
echo timeout /t 8 ^>nul
echo start http://localhost:5173
) > run.bat

echo.
echo ============================================
echo   DONE! Everything is installed.
echo ============================================
echo.
set /p CREATE=Create admin user now? (y/n): 
if /i not "%CREATE%"=="y" goto :askstart
:askuser
set "ADMINUSER="
set /p ADMINUSER=Admin username: 
if "%ADMINUSER%"=="" (
    echo Username cannot be empty.
    goto :askuser
)
cd backend
call venv\Scripts\activate.bat
set USE_SQLITE=1
set DJANGO_DEBUG=1
python manage.py create_admin "%ADMINUSER%"
cd ..

:askstart
echo.
set /p START=Start the app now? (y/n): 
if /i "%START%"=="y" call run.bat
echo.
echo Next time just double-click run.bat
echo To reset an admin password or 2FA later: open backend, run venv\Scripts\activate, set USE_SQLITE=1, then python manage.py create_admin USERNAME
pause
exit /b 0

:fail
echo.
echo [ERROR] Something failed. Scroll up to read the error message.
pause
exit /b 1
