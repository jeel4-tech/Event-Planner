@echo off
echo Starting Django Development Server...
echo.
cd /d "%~dp0"
start "Django Server" cmd /k "python manage.py runserver"
timeout /t 3 /nobreak >nul
start msedge http://127.0.0.1:8000
echo.
echo Server is running! Press any key to stop the server...
pause
