# RUNTIME CONTRACT

## Purpose
This document defines the **minimum runtime contract** for the current approved baseline.

This project is currently operated using:

- **Windows local host machine**
- **PowerShell startup scripts**
- **Task Scheduler**
- **Cloudflare Quick Tunnel** for temporary public access

This contract is intentionally minimal and does **not** introduce any refactor or logic changes.

---

## Current Runtime Model

### Backend Runtime
The backend is started locally via:

- `start_trend_yemen.ps1`

It is responsible for:

- entering the project directory
- activating the Python virtual environment
- loading runtime environment variables
- loading `GOOGLE_CREDENTIALS`
- starting `python main.py`

### Public Access Runtime
Public access is currently provided via:

- `start_quick_tunnel.ps1`

It is responsible for:

- opening a Cloudflare Quick Tunnel
- exposing local backend port `5000`
- writing the latest public tunnel URL to a log file

### Recovery Runtime
Operational recovery is currently provided via:

- `check_and_recover_trend_yemen.ps1`

It is responsible for:

- checking local `/health`
- starting the backend task if needed
- starting the Quick Tunnel task
- printing the latest public tunnel URL
- verifying final health

---

## Required Runtime Assumptions

### 1. Operating System
Current approved fallback runtime is:

- **Windows 10/11**
- **PowerShell**
- **Task Scheduler**

### 2. Python
Python must be installed and available in PATH.

Recommended runtime pattern:

- local virtual environment in `.venv`

### 3. Required Local Files
The following local files are expected to exist:

- `main.py`
- `requirements.txt`
- `.venv\`
- `trend-yemen-service.json` (local only, not committed)
- local startup scripts

### 4. Required Environment Variables
The current runtime expects the following values:

- `GEMINI_API_KEY`
- `SPREADSHEET_ID`
- `DRIVE_FOLDER_ID`
- `CJ_API_KEY`
- `CJ_EMAIL`
- `CJ_PASSWORD`
- `PEXELS_API_KEY`
- `PIXABAY_API_KEY`
- `GOOGLE_CREDENTIALS`

### 5. Google Credentials Contract
For the current local runtime, `GOOGLE_CREDENTIALS` is loaded from:

- `trend-yemen-service.json`

The service account file must remain local and must **not** be committed to GitHub.

---

## Health Contract

### Local Health
The backend must respond on:

- `http://127.0.0.1:5000/health`

Expected shape:

```json
{"orchestrator_running":true,"service":"trend-yemen-backend","status":"ok"}



Admin UI
The Admin UI must be available on:
http://127.0.0.1:5000/admin/ui
Public Access Contract
Current Public Access Type
The current fallback path uses:
Cloudflare Quick Tunnel
Important Limitation
Quick Tunnel is:
temporary
non-stable
not a permanent production URL
expected to change between restarts
Current Tunnel Origin
Quick Tunnel must point to:
http://127.0.0.1:5000
Logging Contract
Logs are written locally to:
logs\backend_latest.log
logs\quick_tunnel_latest.log
logs\quick_tunnel_url.txt
Log Expectations
backend log contains latest backend startup and runtime output
quick tunnel log contains latest cloudflared runtime output
quick tunnel URL file contains the latest detected trycloudflare.com URL
Task Scheduler Contract
The following scheduled tasks are expected to exist:
1. Trend Yemen Backend
Purpose:
starts backend runtime after user logon
2. Trend Yemen Quick Tunnel
Purpose:
starts Cloudflare Quick Tunnel after user logon
Runtime note
Tasks are intended for operational convenience on the local host fallback path.
Recovery Contract
Recovery Script
The current one-click recovery script is:
check_and_recover_trend_yemen.ps1
Expected Behavior
It should:
check local health
start backend task if needed
start quick tunnel task
read latest tunnel URL
perform final health check
Time Sync Requirement
System time must remain correct.
If Windows time becomes incorrect after reboot, Google authentication may fail and backend startup may appear broken.
Operational rule:
fix time sync first
then rerun recovery
Security Contract
The following must remain local only and must not be pushed to GitHub:
real secrets
real .env
trend-yemen-service.json
.venv\
logs\
quick_tunnel_url.txt
Only sanitized templates should be committed.
What This Contract Does Not Guarantee
This current fallback runtime does not provide:
stable permanent public hostname
named Cloudflare tunnel
production VM hosting
external monitoring
advanced process supervision
production-grade service isolation
Approved Current Outcome
The currently approved baseline provides:
working local runtime
working admin UI
working backend orchestrator loop
working retry and stuck handling layers
working temporary public access through Quick Tunnel
lightweight operational recovery
lightweight logging
This is the approved fallback operational baseline until a future stable-hostname phase is started.
