#Requires -Version 5.1
# Nexarq Installer for Windows
#
# One-liner (recommended):
#   irm https://raw.githubusercontent.com/nexarq/nexarq/main/scripts/install.ps1 | iex
#
# Or run a local copy:
#   powershell -ExecutionPolicy Bypass -File .\install.ps1

$ErrorActionPreference = "Stop"

# Force UTF-8 output so Unicode block characters render correctly
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding             = [System.Text.Encoding]::UTF8

function Write-Ok   { param($msg) Write-Host "  " -NoNewline; Write-Host "+" -ForegroundColor Green  -NoNewline; Write-Host "  $msg" }
function Write-Warn { param($msg) Write-Host "  " -NoNewline; Write-Host "!" -ForegroundColor Yellow -NoNewline; Write-Host "  $msg" }
function Write-Fail { param($msg) Write-Host "  " -NoNewline; Write-Host "x" -ForegroundColor Red    -NoNewline; Write-Host "  $msg"; exit 1 }
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


# -- 1. Ensure Node.js 18+ -----------------------------------------------------
Write-Step "Checking Node.js..."

function Get-NodeMajorVersion {
    try {
        $ver = (node --version 2>$null).TrimStart('v')
        if ($ver) { return [int]($ver.Split('.')[0]) }
    } catch {}
    return 0
}

$nodeMajor = Get-NodeMajorVersion

if ($nodeMajor -lt 18) {
    if ($nodeMajor -gt 0) {
        Write-Warn "Node.js v$nodeMajor found but 18+ is required."
    } else {
        Write-Warn "Node.js not found."
    }

    Write-Step "Installing Node.js LTS..."

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    $scoop  = Get-Command scoop  -ErrorAction SilentlyContinue
    $choco  = Get-Command choco  -ErrorAction SilentlyContinue

    if ($winget) {
        Write-Step "Using winget..."
        winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
    } elseif ($choco) {
        Write-Step "Using Chocolatey..."
        choco install nodejs-lts -y
    } elseif ($scoop) {
        Write-Step "Using Scoop..."
        scoop install nodejs-lts
    } else {
        Write-Step "Downloading Node.js installer..."
        $nodeInstaller = "$env:TEMP\node-installer.msi"
        $nodeUrl = "https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi"
        (New-Object System.Net.WebClient).DownloadFile($nodeUrl, $nodeInstaller)
        Start-Process msiexec.exe -ArgumentList "/i `"$nodeInstaller`" /quiet /norestart" -Wait
        Remove-Item $nodeInstaller -Force -ErrorAction SilentlyContinue
    }

    # Refresh PATH from registry
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")

    $nodeMajor = Get-NodeMajorVersion
    if ($nodeMajor -lt 18) {
        Write-Fail "Node.js 18+ install failed. Install from https://nodejs.org then re-run."
    }
}

$nodeVersion = (node --version 2>$null)
Write-Ok "Node.js $nodeVersion"

$npmVersion = (npm --version 2>$null)
Write-Ok "npm $npmVersion"


# -- 2. Install nexarq via npm -------------------------------------------------
Write-Step "Installing nexarq..."

$npmOutput = & npm install -g nexarq 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Ok "nexarq installed"
} else {
    Write-Warn "npm install failed:"
    $npmOutput | Select-Object -First 10 | ForEach-Object {
        Write-Host "      $_" -ForegroundColor DarkGray
    }

    # Fallback: install to user-local prefix to avoid permission issues
    Write-Step "Retrying with user-local prefix..."
    $npmGlobalDir = "$env:APPDATA\npm"
    New-Item -ItemType Directory -Force -Path $npmGlobalDir | Out-Null
    & npm config set prefix $npmGlobalDir

    & npm install -g nexarq 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "npm install failed. Run: npm install -g nexarq"
    }

    # Add npm global bin to user PATH if missing
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH","User")
    if ($userPath -notlike "*$npmGlobalDir*") {
        [System.Environment]::SetEnvironmentVariable("PATH","$npmGlobalDir;$userPath","User")
        $env:PATH = "$npmGlobalDir;$env:PATH"
        Write-Ok "Added $npmGlobalDir to PATH"
    }
    Write-Ok "nexarq installed to $npmGlobalDir"
}


# -- 3. Verify binary is reachable ---------------------------------------------
Write-Step "Verifying installation..."

# Refresh PATH so newly installed bin is found
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("PATH","User")

$nexarqVersion = $null
try { $nexarqVersion = (nexarq --version 2>$null) } catch {}

if ($nexarqVersion) {
    Write-Ok "nexarq $nexarqVersion"
} else {
    Write-Warn "nexarq not found in PATH yet. You may need to restart your terminal."
}


# -- 4. Run init wizard --------------------------------------------------------
Write-Host ""
try {
    nexarq init
} catch {
    Write-Warn "Init skipped — run 'nexarq init' manually to configure."
}


# -- Done ----------------------------------------------------------------------
Write-Host ""
Write-Host "  ----------------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  nexarq is ready." -ForegroundColor Green
Write-Host ""
Write-Host "  Open a new terminal if nexarq is not found, then:" -ForegroundColor DarkGray
Write-Host ""
Write-Host "    nexarq doctor" -ForegroundColor Cyan -NoNewline
Write-Host "   check your setup" -ForegroundColor DarkGray
Write-Host "    nexarq run" -ForegroundColor Cyan -NoNewline
Write-Host "      review your last commit" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Every git commit now triggers an automatic code review." -ForegroundColor DarkGray
Write-Host ""
