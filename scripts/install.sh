#!/usr/bin/env bash
# Nexarq Installer for Linux / macOS
#
# One-liner (recommended):
#   curl -fsSL https://raw.githubusercontent.com/nexarq/nexarq/main/scripts/install.sh | bash
#
# Or run a local copy:
#   ./install.sh

set -e

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


# ── 1. Ensure Node.js / npm ───────────────────────────────────────────────────
step "Checking Node.js..."

ensure_node() {
    if command -v node &>/dev/null; then
        local node_ver
        node_ver=$(node --version 2>/dev/null | sed 's/v//')
        local node_major
        node_major=$(echo "$node_ver" | cut -d. -f1)
        if [ "$node_major" -ge 18 ]; then
            ok "Node.js v${node_ver}"
            return 0
        fi
        warn "Node.js v${node_ver} found but 18+ is required"
    fi

    warn "Node.js 18+ not found. Installing via nvm..."

    # Try nvm if present
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        # shellcheck source=/dev/null
        source "$HOME/.nvm/nvm.sh"
        nvm install --lts
        nvm use --lts
        ok "Node.js $(node --version) installed via nvm"
        return 0
    fi

    # Install nvm
    step "Fetching nvm installer..."
    if command -v curl &>/dev/null; then
        curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    elif command -v wget &>/dev/null; then
        wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    else
        fail "Neither curl nor wget found. Install Node.js 18+ from https://nodejs.org then re-run."
    fi

    # shellcheck source=/dev/null
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"

    nvm install --lts
    nvm use --lts
    ok "Node.js $(node --version) installed via nvm"
}

ensure_node


# ── 2. Install nexarq via npm ─────────────────────────────────────────────────
step "Installing nexarq..."

if npm install -g nexarq 2>/tmp/nexarq-npm-err; then
    ok "nexarq installed"
else
    warn "npm install failed:"
    cat /tmp/nexarq-npm-err | head -10 | while IFS= read -r line; do
        printf "  ${DG}%s${NC}\n" "$line"
    done
    rm -f /tmp/nexarq-npm-err

    # Fallback: try with --unsafe-perm for systems with restrictive npm global dir
    step "Retrying with --prefix $HOME/.npm-global..."
    mkdir -p "$HOME/.npm-global"
    npm config set prefix "$HOME/.npm-global"
    npm install -g nexarq || fail "npm install failed. See above for details."

    # Add npm-global bin to PATH for this session and profile
    NPM_BIN="$HOME/.npm-global/bin"
    export PATH="$NPM_BIN:$PATH"
    PATH_LINE="export PATH=\"\$HOME/.npm-global/bin:\$PATH\""
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ] && ! grep -q ".npm-global" "$rc"; then
            printf "\n# Added by Nexarq installer\n%s\n" "$PATH_LINE" >> "$rc"
        fi
    done
    ok "nexarq installed to $NPM_BIN"
fi

rm -f /tmp/nexarq-npm-err


# ── 3. Verify binary is reachable ─────────────────────────────────────────────
step "Verifying installation..."

NEXARQ_VERSION=$(nexarq --version 2>/dev/null || true)
if [ -z "$NEXARQ_VERSION" ]; then
    warn "nexarq not in PATH yet. Adding npm global bin..."
    NPM_GLOBAL_BIN=$(npm root -g 2>/dev/null | sed 's|/lib/node_modules||')/bin
    export PATH="$NPM_GLOBAL_BIN:$PATH"
    NEXARQ_VERSION=$(nexarq --version 2>/dev/null || true)
fi

if [ -z "$NEXARQ_VERSION" ]; then
    warn "Could not verify nexarq binary. You may need to restart your terminal."
else
    ok "nexarq ${NEXARQ_VERSION}"
fi


# ── 4. Run init wizard ────────────────────────────────────────────────────────
printf "\n"
nexarq init || warn "Init skipped — run 'nexarq init' manually to configure."


# ── Done ──────────────────────────────────────────────────────────────────────
printf "\n"
printf "  ${DG}──────────────────────────────────────────────────────────${NC}\n"
printf "\n"
printf "  ${GR}nexarq is ready.${NC}\n"
printf "\n"
printf "  ${DG}Open a new terminal if nexarq is not found, then:${NC}\n"
printf "\n"
printf "    ${CY}nexarq doctor${NC}${DG}   check your setup${NC}\n"
printf "    ${CY}nexarq run${NC}${DG}      review your last commit${NC}\n"
printf "\n"
printf "  ${DG}Every git commit now triggers an automatic code review.${NC}\n"
printf "\n"
