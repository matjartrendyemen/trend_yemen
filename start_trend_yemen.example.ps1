Set-Location "D:\MTY\trend_yemen"

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"

$logDir = Join-Path $PWD "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$backendLog = Join-Path $logDir "backend_latest.log"

"==================================================" | Out-File -FilePath $backendLog -Append -Encoding utf8
"[{0}] Starting Trend Yemen Backend" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss") | Out-File -FilePath $backendLog -Append -Encoding utf8

& ".\.venv\Scripts\Activate.ps1"

# Replace the placeholder values below with real local secrets.
# Do NOT commit real values to GitHub.

$env:GEMINI_API_KEY="REPLACE_ME"
$env:SPREADSHEET_ID="REPLACE_ME"
$env:DRIVE_FOLDER_ID="REPLACE_ME"
$env:CJ_API_KEY="REPLACE_ME"
$env:CJ_EMAIL="REPLACE_ME"
$env:CJ_PASSWORD="REPLACE_ME"
$env:PEXELS_API_KEY="REPLACE_ME"
$env:PIXABAY_API_KEY="REPLACE_ME"

# Local Google service account file.
# Keep this file local only and never commit it.
$env:GOOGLE_CREDENTIALS = [System.IO.File]::ReadAllText("D:\MTY\trend_yemen\trend-yemen-service.json")

Start-Transcript -Path $backendLog -Append | Out-Null
python main.py
Stop-Transcript | Out-Null
