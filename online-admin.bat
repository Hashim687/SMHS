@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0backend"
echo ============================================
echo   Create / reset admin on the ONLINE database
echo ============================================
echo Paste your Neon connection string (starts with postgresql://)
set /p DBURL=Connection string: 
if "!DBURL!"=="" (
    echo Nothing entered.
    pause
    exit /b 1
)
set "DATABASE_URL=!DBURL!"
call venv\Scripts\activate.bat
python manage.py migrate --noinput
if errorlevel 1 goto :fail
python manage.py createcachetable
set /p ADMINUSER=Admin username: 
python manage.py create_admin "!ADMINUSER!"
echo.
echo Done. Open your website, go to the staff page and sign in.
pause
exit /b 0
:fail
echo [ERROR] Could not reach the database. Check the connection string.
pause
exit /b 1
