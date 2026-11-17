# StreamCut Studio - Start Backend
$env:Path = "C:\Users\fbc\AppData\Local\Programs\ffmpeg\ffmpeg-9.0.2-essentials_build\bin;" + $env:Path
Set-Location "$PSScriptRoot\backend"
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
