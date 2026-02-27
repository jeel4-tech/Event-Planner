# PowerShell script to start Django server and open Edge
Write-Host "Starting Django Development Server..." -ForegroundColor Green
Write-Host ""

# Change to script directory
Set-Location $PSScriptRoot

# Start Django server in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot'; python manage.py runserver" -WindowStyle Normal

# Wait a moment for server to start
Start-Sleep -Seconds 3

# Open Edge browser
Start-Process "msedge.exe" -ArgumentList "http://127.0.0.1:8000"

Write-Host ""
Write-Host "Server is running in a separate window!" -ForegroundColor Green
Write-Host "Edge browser should open automatically." -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit this script (server will continue running)..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
