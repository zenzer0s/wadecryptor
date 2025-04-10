#!/bin/bash

# === Setup Colors ===
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}📦 Updating Termux...${NC}"
pkg update -y && pkg upgrade -y
pkg install -y python git

echo -e "${GREEN}🐍 Setting up virtual environment...${NC}"
python -m venv venv

# Full python path
PYTHON_BIN="$(pwd)/venv/bin/python"

echo -e "${GREEN}📦 Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install pycryptodome tqdm rich

SCRIPT="wadecryptor.py"
if [ ! -f "$SCRIPT" ]; then
  echo -e "${RED}❌ Error: ${SCRIPT} not found in $(pwd)"
  exit 1
fi

echo -e "${GREEN}🚀 Running with root via su...${NC}"

# Run the Python script inside root shell with full path
su -c "$PYTHON_BIN $(pwd)/$SCRIPT"
