#Requires -Version 5.1
# Nexarq Installer for Windows
#
# One-liner (recommended):
#   irm https://raw.githubusercontent.com/nexarq/nexarq-cli/main/install.ps1 | iex
#
# Or run a local copy:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"

# Force UTF-8 output so Unicode block characters render correctly
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding             = [System.Text.Encoding]::UTF8

$NexarqHome = "$env:USERPROFILE\.nexarq"
$VenvDir    = "$NexarqHome\venv"
$BinDir     = "$NexarqHome\bin"
$NexarqExe  = "$VenvDir\Scripts\nexarq.exe"
$ShimPath   = "$BinDir\nexarq.cmd"

function Write-Ok   { param($msg) Write-Host "  " -NoNewline; Write-Host "+" -ForegroundColor Green -NoNewline; Write-Host "  $msg" }
function Write-Warn { param($msg) Write-Host "  " -NoNewline; Write-Host "!" -ForegroundColor Yellow -NoNewline; Write-Host "  $msg" }
function Write-Fail { param($msg) Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red -NoNewline; Write-Host "  $msg"; exit 1 }
function Write-Step { param($msg) Write-Host "  " -NoNewline; Write-Host "-" -ForegroundColor DarkGray -NoNewline; Write-Host "  $msg" }


# -- Banner --------------------------------------------------------------------
Clear-Host
Write-Host ""
Write-Host "  ##  ##  #######  ##    ##  #####   #####    #####  " -ForegroundColor Cyan
Write-Host "  ### ##  ##        ##  ##  ##   ##  ##  ##  ##   ## " -ForegroundColor Cyan
Write-Host "  ## ###  #####      ####   #######  #####   ##   ## " -ForegroundColor Cyan
Write-Host "  ##  ##  ##        ##  ##  ##   ##  ##  ##  ####### " -ForegroundColor Cyan
Write-Host "  ##  ##  #######  ##    ##  ##   ##  ##  ##  ##   ## " -ForegroundColor Cyan
Write-Host ""
Write-Host "     AI-powered code review  -  runs on every commit" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  ----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Installing..." -ForegroundColor White
Write-Host ""


# -- Progress-aware pip installer ----------------------------------------------
# Pure stdlib Python - works before nexarq is installed.
$_PipScript = @'
import subprocess, sys, re, threading, time, io

# Force UTF-8 output so block characters render correctly on any terminal
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

def _bar(pct, width=32):
    f = min(int(pct / 100 * width), width)
    return "\u2588" * f + "\u2591" * (width - f)

def _fmt(mb):
    return "{:.1f} MB".format(mb)

pip_exe  = sys.argv[1]
pkg_args = sys.argv[2:]

state = {"phase": "prepare", "total_mb": 0.0, "done": False}

def _animate():
    pct = 0.0
    while not state["done"]:
        p     = state["phase"]
        total = state["total_mb"]
        if p == "download" and total > 0:
            pct = min(pct + max((95.0 - pct) * 0.10, 0.4), 95.0)
            sys.stdout.write("\r  Downloading... [{}] {}% of {}  ".format(
                _bar(pct), int(pct), _fmt(total)))
            sys.stdout.flush()
        elif p == "install":
            sys.stdout.write("\r  Installing packages\u2026                                      ")
            sys.stdout.flush()
        time.sleep(0.12)

threading.Thread(target=_animate, daemon=True).start()

proc = subprocess.Popen(
    [pip_exe, "install", "--progress-bar", "off"] + pkg_args,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1, encoding="utf-8", errors="replace",
)

error_lines = []
for raw in proc.stdout:
    line = raw.strip()

    m = re.search(r"Downloading\s+\S+\s+\(([0-9.]+)\s*(MB|kB|B)\)", line)
    if m:
        size, unit = float(m.group(1)), m.group(2)
        mb = size if unit == "MB" else (size / 1024.0 if unit == "kB" else size / 1_048_576)
        if mb > state["total_mb"]:
            state["total_mb"] = mb
        state["phase"] = "download"
        continue

    if "Installing collected" in line:
        total = state["total_mb"]
        if total > 0 and state["phase"] == "download":
            sys.stdout.write("\r  Downloading... [{}] 100% of {}  \n".format(
                _bar(100), _fmt(total)))
            sys.stdout.flush()
        state["phase"] = "install"
        continue

    if line.startswith("Successfully installed"):
        state["done"] = True
        pkgs = line.replace("Successfully installed", "").strip()
        sys.stdout.write("\r  \u2713  {}                              \n".format(pkgs))
        sys.stdout.flush()
        continue

    if "already satisfied" in line.lower():
        state["done"] = True
        pkg = line.split()[2] if len(line.split()) >= 3 else ""
        sys.stdout.write("\r  \u2713  {} (already installed)                \n".format(pkg))
        sys.stdout.flush()
        continue

    if re.search(r"\b(error|ERROR|failed|FAILED)\b", line) and "already" not in line.lower():
        error_lines.append(line)

state["done"] = True
proc.wait()

if error_lines:
    sys.stdout.write("\n")
    for e in error_lines:
        sys.stdout.write("  ! {}\n".format(e))
    sys.stdout.flush()

sys.exit(proc.returncode)
'@

function Invoke-PipInstall {
    param([string]$PipExe, [string[]]$PackageArgs)
    $tmp = [System.IO.Path]::ChangeExtension(
        [System.IO.Path]::GetTempFileName(), ".py")
    [System.IO.File]::WriteAllText($tmp, $_PipScript, [System.Text.Encoding]::UTF8)
    $pyExe = Join-Path (Split-Path $PipExe -Parent) "python.exe"
    try {
        & $pyExe $tmp $PipExe @PackageArgs
        return $LASTEXITCODE
    } finally {
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    }
}


# -- 1. Find Python 3.10+ ------------------------------------------------------
Write-Step "Checking Python..."

$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd -c "import sys; v=sys.version_info; print(str(v.major)+'.'+str(v.minor))" 2>$null
        if ($ver) {
            $parts = $ver.Trim().Split(".")
            if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10) {
                $python = $cmd
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Warn "Python 3.10+ not found. Trying to install..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    } else {
        Write-Warn "winget not available. Downloading Python 3.12..."
        $pyInstaller = "$env:TEMP\python-installer.exe"
        (New-Object System.Net.WebClient).DownloadFile(
            "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe",
            $pyInstaller
        )
        Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait
        Remove-Item $pyInstaller -Force
    }

    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")

    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $ver = & $cmd -c "import sys; v=sys.version_info; print(str(v.major)+'.'+str(v.minor))" 2>$null
            if ($ver) {
                $parts = $ver.Trim().Split(".")
                if ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10) { $python = $cmd; break }
            }
        } catch {}
    }
    if (-not $python) { Write-Fail "Python 3.10+ still not found. Install from https://python.org then re-run." }
}

$pyVersion = (& $python --version 2>&1).ToString().Trim()
Write-Ok $pyVersion


# -- 2. Create venv ------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $NexarqHome | Out-Null

if (Test-Path $VenvDir) {
    Write-Step "Refreshing existing environment..."
    try {
        Remove-Item -Recurse -Force $VenvDir -ErrorAction Stop
    } catch {
        Write-Warn "Could not remove existing venv (files in use?). Trying in-place upgrade..."
    }
}

Write-Step "Creating virtual environment..."
& $python -m venv $VenvDir
if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to create virtual environment." }
Write-Ok "Virtual environment ready"


# -- 3. Upgrade pip (silent) ---------------------------------------------------
& "$VenvDir\Scripts\python.exe" -m pip install --upgrade --quiet pip 2>$null | Out-Null


# -- 4. Install nexarq-cli with live progress bar ------------------------------
Write-Host ""

$_localSource = $null
if ($PSScriptRoot -and (Test-Path (Join-Path $PSScriptRoot "pyproject.toml"))) {
    $_localSource = $PSScriptRoot
} elseif (Test-Path (Join-Path $PWD "pyproject.toml")) {
    $_localSource = $PWD
}

if ($_localSource) {
    $exitCode = Invoke-PipInstall -PipExe "$VenvDir\Scripts\pip.exe" -PackageArgs @("-e", "$_localSource")
} else {
    $exitCode = Invoke-PipInstall -PipExe "$VenvDir\Scripts\pip.exe" -PackageArgs @("nexarq-cli")
}

Write-Host ""
if ($exitCode -ne 0) { Write-Fail "Package installation failed." }
Write-Ok "nexarq-cli ready"


# -- 5. Create global shim -----------------------------------------------------
Write-Step "Creating nexarq command..."
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

[System.IO.File]::WriteAllText(
    $ShimPath,
    "@echo off`r`n`"$NexarqExe`" %*`r`n",
    [System.Text.Encoding]::ASCII
)
[System.IO.File]::WriteAllText(
    "$BinDir\nexarq.ps1",
    "& `"$NexarqExe`" @args`r`n",
    [System.Text.Encoding]::UTF8
)
Write-Ok "Command shim created"


# -- 6. Add to PATH ------------------------------------------------------------
Write-Step "Adding nexarq to PATH..."

$userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if (-not $userPath) { $userPath = "" }

if ($userPath -notlike "*$BinDir*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$BinDir;$userPath", "User")
    $env:PATH = "$BinDir;$env:PATH"
    Write-Ok "$BinDir added to PATH"
} else {
    Write-Ok "Already in PATH"
}


# -- 7. Git hooks --------------------------------------------------------------
Write-Step "Configuring global git hooks..."
if (Get-Command git -ErrorAction SilentlyContinue) {
    & $NexarqExe install --global --yes
    Write-Ok "Hooks installed - every repo is now covered"
} else {
    Write-Warn "git not found. Run: nexarq install --global"
}


# -- 8. GitHub login -----------------------------------------------------------
Write-Host ""
& $NexarqExe login


# -- Done ----------------------------------------------------------------------
Write-Host ""
Write-Host "  ----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  nexarq is ready." -ForegroundColor Green
Write-Host ""
Write-Host "  Open a new terminal, then:" -ForegroundColor DarkGray
Write-Host ""
Write-Host "    nexarq doctor" -ForegroundColor Cyan -NoNewline
Write-Host "   check your setup" -ForegroundColor DarkGray
Write-Host "    nexarq run" -ForegroundColor Cyan -NoNewline
Write-Host "      review your last commit" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Every git commit now triggers an automatic code review." -ForegroundColor DarkGray
Write-Host ""
