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
source venv/bin/activate

# === Full Python path from venv ===
PYTHON_BIN="$(pwd)/venv/bin/python"
SCRIPT="wadecryptor.py"

echo -e "${GREEN}📦 Installing dependencies...${NC}"
pip install --upgrade pip
pip install pycryptodome tqdm rich

# === Check Python script ===
if [ ! -f "$SCRIPT" ]; then
  echo -e "${RED}❌ Error: ${SCRIPT} not found in $(pwd)${NC}"
  exit 1
fi

# === Define paths ===
KEY_SOURCE="/data/data/com.whatsapp/files/key"
KEY_DEST="$(pwd)/key"

DB_SRC="/data/data/com.whatsapp/databases/msgstore.db*"
DB_DEST="/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases"

MARKDOWN_DIR="$DB_DEST/markdown"

echo -e "${GREEN}🔐 Copying WhatsApp key...${NC}"

if [ ! -f "$KEY_DEST" ]; then
  su -c "dd if='$KEY_SOURCE' of='$KEY_DEST' status=none"
  [ -f "$KEY_DEST" ] && echo -e "${GREEN}✅ Key extracted!${NC}" || { echo -e "${RED}❌ Failed to extract key.${NC}"; exit 1; }
else
  echo -e "${GREEN}✅ Key already exists.${NC}"
fi

echo -e "${GREEN}🗃️ Copying .crypt database files...${NC}"
su -c "cp $DB_SRC $DB_DEST && chmod 644 $DB_DEST/msgstore.db*"

if ls $DB_DEST/msgstore.db* >/dev/null 2>&1; then
  echo -e "${GREEN}✅ Database files copied!${NC}"
else
  echo -e "${RED}❌ Failed to copy database files.${NC}"
  exit 1
fi

echo -e "${GREEN}📁 Ensuring markdown output folder exists...${NC}"
mkdir -p "$MARKDOWN_DIR"

# === Run decryption script ===
echo -e "${GREEN}🚀 Running wadecryptor.py as root...${NC}"
su -c "$PYTHON_BIN $(pwd)/$SCRIPT"
