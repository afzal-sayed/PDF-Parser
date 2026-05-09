#!/bin/bash

echo ""
echo " ============================================"
echo "  NEET Selection List Parser"
echo " ============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo " [ERROR] Python 3 not found. Run ./install.sh first."
    exit 1
fi

# Check Flask is installed
if ! python3 -c "import flask" &>/dev/null; then
    echo " [ERROR] Dependencies missing. Run ./install.sh first."
    exit 1
fi

echo " [OK] Starting server..."
echo ""
echo " ============================================"
echo "  App is running at: http://127.0.0.1:5000"
echo "  Press Ctrl+C to stop the server"
echo " ============================================"
echo ""

# Open browser (best-effort, different on macOS vs Linux)
(sleep 1 && \
    if command -v xdg-open &>/dev/null; then xdg-open http://127.0.0.1:5000; \
    elif command -v open &>/dev/null; then open http://127.0.0.1:5000; \
    fi) &

python3 app.py
