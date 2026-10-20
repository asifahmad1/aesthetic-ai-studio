#!/usr/bin/env bash
# ============================================================
#  Aesthetic AI Studio v1 - macOS / Linux launcher
#  Run:  bash start.sh   (or: chmod +x start.sh && ./start.sh)
# ============================================================
set -e
cd "$(dirname "$0")"

echo ""
echo " ========================================================"
echo "  Aesthetic AI Studio v1"
echo "  Your local AI presentation generator"
echo " ========================================================"
echo ""

# --- 1. Find Python ---------------------------------------------------
if command -v python3 >/dev/null 2>&1; then
    PYCMD="python3"
else
    echo "[ERROR] python3 was not found."
    echo "Install Python 3.10+ from https://www.python.org/downloads/"
    echo "  macOS:    brew install python3"
    echo "  Ubuntu:   sudo apt install python3 python3-venv"
    exit 1
fi
$PYCMD --version

# --- 2. Virtual environment -------------------------------------------
if [ ! -x "venv/bin/python" ]; then
    echo ""
    echo "[1/3] First run: creating a private Python environment (one-time)..."
    $PYCMD -m venv venv
fi
# shellcheck disable=SC1091
source "venv/bin/activate"

# --- 3. Install requirements if imports fail ---------------------------
if ! python -c "import flask, pptx, reportlab, pypdf" 2>/dev/null; then
    echo ""
    echo "[2/3] Installing required packages (one-time, needs internet)..."
    python -m pip install --upgrade pip >/dev/null 2>&1 || true
    pip install -r requirements.txt
else
    echo "[2/3] Packages already installed - skipping."
fi

# --- 4. Start the app ---------------------------------------------------
echo ""
echo "[3/3] Starting Aesthetic AI Studio..."
echo ""
echo " Opening http://127.0.0.1:4321 in your browser."
echo " Keep this terminal open while you use the app (Ctrl+C to stop)."
echo ""
sleep 2
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:4321" >/dev/null 2>&1 &
elif command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:4321" >/dev/null 2>&1 &
fi
python app.py
