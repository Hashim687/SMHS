@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0backend"
echo ============================================
echo   Create / reset admin on the ONLINE database
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is not installed. Install it from https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist venv\Scripts\python.exe (
    echo First run: installing Python packages, please wait...
    if exist venv rmdir /s /q venv
    python -m venv venv
    if errorlevel 1 goto :fail
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install --prefer-binary -r requirements.txt
    if errorlevel 1 goto :fail
) else (
    call venv\Scripts\activate.bat
)

echo.
echo Paste your Neon connection string (starts with postgresql://)
set /p DBURL=Connection string: 
if "!DBURL!"=="" (
    echo Nothing entered.
    pause
    exit /b 1
)
set "DATABASE_URL=!DBURL!"
python manage.py migrate --noinput
if errorlevel 1 goto :dbfail
python manage.py createcachetable
set /p ADMINUSER=Admin username: 
python manage.py create_admin "!ADMINUSER!"
echo.
echo Done. Open your website, go to the staff page and sign in.
pause
exit /b 0

:dbfail
echo [ERROR] Could not reach the database. Check the connection string.
pause
exit /b 1

:fail
echo [ERROR] Setup of Python packages failed. Scroll up to read the error.
pause
exit /b 1
