# StreamCut Studio - Launch Full Application
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting StreamCut Studio (Self-Hosted AI Video Clipper)" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start_backend.ps1"
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start_frontend.ps1"

Write-Host "Services launched!" -ForegroundColor Green
Write-Host "Backend API: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Frontend UI: http://127.0.0.1:3000" -ForegroundColor Yellow
Start-Process "http://127.0.0.1:3000"
