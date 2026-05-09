#!/bin/bash
set -e

echo ""
echo " ============================================"
echo "  NEET Selection List Parser - Setup"
echo " ============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo " [ERROR] Python 3 is not installed."
    echo " Install it via your package manager:"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "   macOS:         brew install python"
    exit 1
fi

echo " [OK] Found $(python3 --version)"

# Upgrade pip
echo " [..] Upgrading pip..."
python3 -m pip install --upgrade pip --quiet
echo " [OK] pip is up to date"

# Install requirements
echo " [..] Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt --quiet
echo " [OK] All dependencies installed"

# Create .env if missing
if [ ! -f ".env" ]; then
    echo "MAX_UPLOAD_MB=500" > .env
    echo " [OK] Created .env with default settings"
else
    echo " [OK] .env already exists"
fi

echo ""
echo " ============================================"
echo "  Setup complete! Run ./start.sh to launch."
echo " ============================================"
echo ""
