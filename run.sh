#!/bin/bash

# === Setup Colors ===
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}📦 Updating Termux...${NC}"
pkg update -y && pkg upgrade -y

echo -e "${GREEN}🐍 Installing Python...${NC}"
pkg install -y python git

echo -e "${GREEN}📁 Creating Virtual Environment...${NC}"
python -m venv venv
source venv/bin/activate

echo -e "${GREEN}📦 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install pycryptodome tqdm rich

# === Check if Python script exists ===
SCRIPT="wadecryptor.py"
if [ ! -f "$SCRIPT" ]; then
  echo -e "${RED}❌ Error: ${SCRIPT} not found in $(pwd)"
  echo -e "📎 Please make sure your Git repo includes '${SCRIPT}'"
  exit 1
fi

echo -e "${GREEN}🚀 Running $SCRIPT...${NC}"
python "$SCRIPT"
