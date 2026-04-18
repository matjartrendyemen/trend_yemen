# RUNTIME CONTRACT

## Purpose
This document defines the **minimum approved runtime contract** for the current operational baseline.

This runtime is intentionally:

- minimal
- fallback-oriented
- local-host based
- non-refactored
- outside application logic

It does **not** introduce business logic changes, architecture redesign, or application-level scheduling.

---

## Current Approved Runtime Baseline

The project is currently operated using:

- **Windows local host machine**
- **PowerShell startup scripts**
- **Task Scheduler**
- **Cloudflare Quick Tunnel** for temporary public access
- **Local logs + runtime status snapshot + recovery state**
- **Operational recovery outside the application**

This is the approved **fallback/public baseline**.

It is **not** permanent hosting.

---

## Runtime Classification

### Current runtime is:
- local-host runtime
- fallback public runtime
- Quick Tunnel-based public exposure
- temporary public access
- non-permanent hostname
- non-production-grade hosting

### Current runtime is not:
- VM hosting
- permanent public hostname
- named tunnel deployment
- stable domain-based hosting
- production infrastructure
- managed cloud runtime

---

## Core Runtime Model

### Backend Runtime
The backend is started locally via:

- `start_trend_yemen.ps1`

It is responsible for:

- entering the project directory
- activating the Python virtual environment
- loading runtime environment variables
- loading `GOOGLE_CREDENTIALS`
- performing startup readiness checks
- preventing duplicate backend startup
- starting `python main.py`
- updating runtime status snapshot
- writing backend logs

### Public Access Runtime
Public access is currently provided via:

- `start_quick_tunnel.ps1`

It is responsible for:

- opening a Cloudflare Quick Tunnel
- exposing local backend port `5000`
- preventing duplicate tunnel startup
- writing tunnel logs
- writing latest public tunnel URL
- updating runtime status snapshot

### Recovery Runtime
Operational recovery is currently provided via:

- `check_and_recover_trend_yemen.ps1`

It is responsible for:

- checking local `/health`
- checking public fallback `/health`
- applying backend recovery cooldown
- applying tunnel recovery cooldown
- restarting backend task if needed
- restarting tunnel task if needed
- respecting startup readiness constraints
- writing recovery logs
- writing recovery state
- updating runtime status snapshot

---

## Required Runtime Assumptions

### 1. Operating System
Current approved fallback runtime is:

- **Windows 10/11**
- **PowerShell 5.1 compatible**
- **Task Scheduler**

### 2. Python
Python must be installed and available in PATH.

Recommended local runtime pattern:

- `.venv\`

### 3. Required Local Files
The following local files are expected to exist:

- `main.py`
- `requirements.txt`
- `.venv\`
- `trend-yemen-service.json` (local only, not committed)
- local PowerShell startup/recovery scripts

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
Public Fallback Health

When Quick Tunnel is active, public fallback health is expected on:

<latest_trycloudflare_url>/health

This URL is temporary and changes over time.

Public Access Contract
Current Public Access Type

The current fallback/public path uses:

Cloudflare Quick Tunnel
Important Limitation

Quick Tunnel is:

temporary
non-stable
restart-dependent
not a permanent production URL
expected to change between restarts or re-launches
Current Tunnel Origin

Quick Tunnel must point to:

http://127.0.0.1:5000
Permanent Hosting Status

Permanent public hosting is not implemented in the current baseline.

No named tunnel, no fixed hostname, and no stable domain routing are part of the current approved runtime.

Logging Contract

Logs are written locally to:

logs\backend_latest.log
logs\quick_tunnel_latest.log
logs\quick_tunnel_url.txt
logs\recovery_latest.log
logs\recovery_state.json
logs\runtime_status.json
Log Expectations
backend_latest.log

Contains:

backend startup attempts
readiness messages
duplicate-start prevention messages
backend runtime output
quick_tunnel_latest.log

Contains:

quick tunnel startup attempts
duplicate-start prevention messages
cloudflared output
tunnel registration output
quick_tunnel_url.txt

Contains:

latest detected trycloudflare.com URL
recovery_latest.log

Contains:

recovery checks
backend recovery decisions
tunnel recovery decisions
cooldown behavior
startup readiness block reasons
final recovery result
recovery_state.json

Contains recovery state such as:

last check time
last result
local/public health state
last backend recovery time
last tunnel recovery time
latest tunnel URL
backend startup readiness state
backend startup block reason
runtime_status.json

Contains one consolidated runtime snapshot such as:

backend_running
backend_health
backend_process_count
backend_state
tunnel_running
tunnel_process_count
tunnel_state
public_health
latest_tunnel_url
last_recovery_result
startup_block_reason
backend_startup_ready
last_check_at
updated_by
Task Scheduler Contract

The following scheduled tasks are expected to exist:

1. Trend Yemen Backend

Purpose:

starts backend runtime after user logon
2. Trend Yemen Quick Tunnel

Purpose:

starts Cloudflare Quick Tunnel after user logon
3. Trend Yemen Auto Recover

Purpose:

performs automated health-based operational recovery
restarts backend task if local health fails
restarts quick tunnel task if public fallback fails
applies cooldown windows to avoid restart thrashing
respects startup readiness restrictions
Runtime Note

These tasks are part of the current fallback operational model and are intentionally external to application logic.

Recovery Contract
Recovery Script

The current one-click and automated recovery script is:

check_and_recover_trend_yemen.ps1
Expected Behavior

It should:

check local health
check public fallback health
recover backend if needed
recover tunnel if needed
write recovery log
write recovery state
update runtime status snapshot
Cooldown Contract

The current recovery path includes simple cooldown windows to avoid restart thrashing:

backend recovery cooldown
tunnel recovery cooldown
Single-Instance Recovery Behavior

Recovery must not create duplicate backend or duplicate tunnel runtime when a healthy instance is already running.

Boot Readiness Guard

The current backend startup path includes a lightweight startup preflight.

Purpose
reduce false startup failures immediately after reboot
avoid backend recovery noise when Windows time is not yet ready
avoid misleading Google authentication failures caused by invalid system time
Current behavior
checks basic time readiness before backend startup
waits for readiness within a bounded window
allows startup when readiness is confirmed
blocks startup when readiness remains invalid
writes a clear block reason to logs/state
does not change application logic or business flow
Single-Instance Guard Contract

The current fallback runtime includes single-instance guards for:

backend startup
quick tunnel startup
Backend guard behavior

If a main.py process is already running:

check local health
if healthy: skip duplicate startup cleanly
if unhealthy: block duplicate startup to avoid double runtime
Tunnel guard behavior

If a cloudflared tunnel --url http://127.0.0.1:5000 process is already running:

check latest public fallback health
if healthy: skip duplicate startup cleanly
if unhealthy: block duplicate startup to avoid double tunnel runtime
Intent

This prevents:

duplicate backend runtime
duplicate tunnel runtime
repeated PowerShell windows
avoidable port/tunnel conflicts
Hotfix Compatibility Contract

The current PowerShell startup and recovery scripts were hotfixed for:

Windows PowerShell 5.1 syntax compatibility
safe custom function invocation style
removal of invalid custom function call patterns using FunctionName()
Operational rule

All local PowerShell runtime scripts must remain compatible with:

Windows PowerShell 5.1

without requiring PowerShell 7 features.

Time Sync Requirement

System time must remain correct.

If Windows time becomes incorrect after reboot, Google authentication may fail and backend startup may appear broken.

Operational rule

When startup or auth fails after reboot:

verify Windows time
fix time sync
rerun recovery if needed
Security Contract

The following must remain local only and must not be pushed to GitHub:

real secrets
real .env
trend-yemen-service.json
.venv\
logs\
quick_tunnel_url.txt
recovery_state.json
runtime_status.json
any file containing live credentials

Only sanitized templates should be committed.

What This Runtime Does Not Guarantee

This current fallback runtime does not provide:

stable permanent public hostname
named Cloudflare tunnel
stable domain-based routing
production VM hosting
external monitoring
external alerting
advanced service supervision
permanent public infrastructure
production-grade process isolation
zero-touch cloud deployment
Approved Current Outcome

The currently approved baseline provides:

working local runtime
working admin UI
working backend orchestrator loop
working retry and stuck handling layers
working temporary public access through Quick Tunnel
automated operational recovery
startup readiness protection
duplicate-runtime prevention
runtime status snapshot
lightweight logging

This is the approved fallback/public operational baseline until a future permanent-hosting phase is started.
