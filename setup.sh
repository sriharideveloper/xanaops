#!/bin/bash
# ╔══════════════════════════════════════════════════════════════╗
# ║  XANA OS — Setup & Onboarding Script                         ║
# ╚══════════════════════════════════════════════════════════════╝
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}  XANA OS — PROMETHEUS · Setup${RESET}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════${RESET}"
    echo ""
}

step() { echo -e "${CYAN}▸ $1${RESET}"; }
ok()   { echo -e "${GREEN}  ✓ $1${RESET}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${RESET}"; }
fail() { echo -e "${RED}  ✗ $1${RESET}"; }

banner

# ── Python check ─────────────────────────────────────────────
step "Checking Python version..."
if ! command -v python3 &>/dev/null; then
    fail "Python 3 not found. Install Python 3.10+ and re-run."
    exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
ok "Python $PY_VER found"

# ── Virtual environment ───────────────────────────────────────
step "Setting up virtual environment..."
if [ ! -d "xana_env" ]; then
    python3 -m venv xana_env
    ok "Virtual environment created at ./xana_env"
else
    ok "Virtual environment already exists"
fi
source xana_env/bin/activate

# ── Dependencies ──────────────────────────────────────────────
step "Installing dependencies (this may take a few minutes)..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Dependencies installed"

# ── Ollama check ─────────────────────────────────────────────
step "Checking Ollama..."
if command -v ollama &>/dev/null; then
    ok "Ollama is installed"
    if ollama list 2>/dev/null | grep -q "llama3.2"; then
        ok "llama3.2 model is available"
    else
        warn "llama3.2 model not found. Run: ollama pull llama3.2"
        warn "You can also change LLM_MODEL in config.py to any model you have."
    fi
else
    warn "Ollama not found. Install from https://ollama.com"
    warn "ORACLE/AI features won't work without it. Live globe/OSINT still works."
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}  XANA OS setup complete!${RESET}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${RESET}"
echo ""
echo "  To start XANA OS:"
echo -e "    ${CYAN}./start.sh${RESET}  (or: streamlit run app.py)"
echo ""
echo "  To build your memory database from conversation history:"
echo -e "    ${CYAN}Step 1:${RESET}  python legacy/parse_chats.py   # extract ChatGPT exports"
echo -e "    ${CYAN}Step 2:${RESET}  python legacy/1_prep_data.py   # pair messages"
echo -e "    ${CYAN}Step 3:${RESET}  python legacy/build-brain.py   # build vector DB"
echo ""
echo "  See README.md for full documentation."
echo ""
