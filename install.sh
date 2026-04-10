#!/usr/bin/env bash
# Nexarq Installer for Linux / macOS
#
# One-liner (recommended):
#   curl -fsSL https://raw.githubusercontent.com/nexarq/nexarq-cli/main/install.sh | bash
#
# Or run a local copy:
#   ./install.sh

set -e

NEXARQ_HOME="$HOME/.nexarq"
VENV_DIR="$NEXARQ_HOME/venv"
BIN_DIR="$HOME/.local/bin"
SHIM_PATH="$BIN_DIR/nexarq"
NEXARQ_EXE="$VENV_DIR/bin/nexarq"

# Colors
CY='\033[0;36m'    # cyan    — banner
GR='\033[0;32m'    # green   — ok
YE='\033[0;33m'    # yellow  — warn
RD='\033[0;31m'    # red     — error
DG='\033[0;90m'    # dark gray — secondary text
WH='\033[1;37m'    # bright white
NC='\033[0m'       # reset

ok()   { printf "  ${GR}+${NC}  %s\n" "$1"; }
warn() { printf "  ${YE}!${NC}  %s\n" "$1"; }
fail() { printf "  ${RD}x${NC}  %s\n" "$1"; exit 1; }
step() { printf "  ${DG}-${NC}  %s\n" "$1"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
printf "\n\n"

# NEXARQ — block-pixel ASCII art (5-line tall, ANSI Shadow style)
printf "${CY}"
printf "  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \n"
printf "  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88      \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88\n"
printf "  \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88\n"
printf "  \xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88      \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\n"
printf "  \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88   \xe2\x96\x88\xe2\x96\x88 \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88  \xe2\x96\x88\xe2\x96\x88\xe2\x96\x88\xe2\x96\x88 \n"
printf "${NC}"

printf "\n"
printf "  ${DG}AI-powered code review — runs on every commit${NC}\n"
printf "\n"
printf "  ${DG}──────────────────────────────────────────────────────────${NC}\n"
printf "\n"
printf "  ${WH}Installing...${NC}\n"
printf "\n"


# ── Progress-aware pip installer ──────────────────────────────────────────────
_pip_install_with_progress() {
    local pip_exe="$1"
    shift
    local pkg_args=("$@")

    local tmp_script
    tmp_script=$(mktemp /tmp/nexarq-install-XXXXXX.py)

    cat > "$tmp_script" << 'PYEOF'
import subprocess, sys, re, threading, time

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
PYEOF

    local py_exe
    py_exe="$(dirname "$pip_exe")/python"
    [ -x "$py_exe" ] || py_exe="$(dirname "$pip_exe")/python3"

    "$py_exe" "$tmp_script" "$pip_exe" "${pkg_args[@]}"
    local ret=$?
    rm -f "$tmp_script"
    return $ret
}


# ── 1. Find Python 3.10+ ──────────────────────────────────────────────────────
step "Checking Python..."
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    fail "Python 3.10+ not found. Install from https://python.org
       Ubuntu/Debian: sudo apt install python3.11
       macOS:         brew install python@3.11"
fi

pyver=$("$PYTHON" --version 2>&1)
ok "$pyver"


# ── 2. Create venv ────────────────────────────────────────────────────────────
step "Creating virtual environment..."
mkdir -p "$NEXARQ_HOME"
"$PYTHON" -m venv "$VENV_DIR"
ok "Virtual environment ready"


# ── 3. Upgrade pip (silent) ───────────────────────────────────────────────────
"$VENV_DIR/bin/pip" install --upgrade --quiet pip 2>/dev/null


# ── 4. Install nexarq-cli with live progress bar ──────────────────────────────
printf "\n"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || pwd)"

if [ -f "$SCRIPT_DIR/pyproject.toml" ]; then
    _pip_install_with_progress "$VENV_DIR/bin/pip" -e "$SCRIPT_DIR"
else
    _pip_install_with_progress "$VENV_DIR/bin/pip" nexarq-cli
fi

printf "\n"
ok "nexarq-cli ready"


# ── 5. Create global shim ─────────────────────────────────────────────────────
step "Creating nexarq command..."
mkdir -p "$BIN_DIR"

cat > "$SHIM_PATH" <<EOF
#!/bin/sh
exec "$NEXARQ_EXE" "\$@"
EOF
chmod +x "$SHIM_PATH"
ok "Shim created at $SHIM_PATH"


# ── 6. Ensure PATH ────────────────────────────────────────────────────────────
step "Ensuring nexarq is in PATH..."
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

if ! echo "$PATH" | grep -q "$BIN_DIR"; then
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ] && ! grep -q ".local/bin" "$rc"; then
            printf "\n# Added by Nexarq installer\n%s\n" "$PATH_LINE" >> "$rc"
        fi
    done
    export PATH="$BIN_DIR:$PATH"
    ok "$BIN_DIR added to PATH  (restart terminal or: source ~/.bashrc)"
else
    ok "Already in PATH"
fi


# ── 7. Global git hooks ───────────────────────────────────────────────────────
step "Configuring global git hooks..."
"$NEXARQ_EXE" install --global --yes
ok "Hooks installed — every repo is now covered"


# ── 8. GitHub login ───────────────────────────────────────────────────────────
printf "\n"
"$NEXARQ_EXE" login


# ── Done ──────────────────────────────────────────────────────────────────────
printf "\n"
printf "  ${DG}──────────────────────────────────────────────────────────${NC}\n"
printf "\n"
printf "  ${GR}nexarq is ready.${NC}\n"
printf "\n"
printf "  ${DG}Open a new terminal, then:${NC}\n"
printf "\n"
printf "    ${CY}nexarq doctor${NC}${DG}   check your setup${NC}\n"
printf "    ${CY}nexarq run${NC}${DG}      review your last commit${NC}\n"
printf "\n"
printf "  ${DG}Every git commit now triggers an automatic code review.${NC}\n"
printf "\n"
