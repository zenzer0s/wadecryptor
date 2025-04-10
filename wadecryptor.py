import os
import sqlite3
import time
from tqdm import tqdm
from Crypto.Cipher import AES
from rich.console import Console

console = Console()

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(SCRIPT_DIR, "key")  # Use local key file
CRYPT_FILE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt14"
OUTPUT_SQLITE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore_decrypted.db"
OUTPUT_MD_DIR = os.path.expanduser("~/storage/shared/wadecryptor_output")

os.makedirs(OUTPUT_MD_DIR, exist_ok=True)

# === Terminal Animation ===
def decrypting_animation():
    with console.status("[bold green]Decrypting database...") as status:
        for _ in tqdm(range(30), desc="Decrypting", ncols=75):
            time.sleep(0.05)

# === Load and fix AES key ===
def load_key(key_path):
    with open(key_path, 'rb') as f:
        raw = f.read()
        if len(raw) >= 32:
            return raw[:32]  # Take first 32 bytes instead of last 32
        else:
            raise ValueError(f"Key file too small: {len(raw)} bytes")

# === AES Decryption Function ===
def decrypt_crypt14(key_path, crypt_path, output_path):
    try:
        key = load_key(key_path)
        console.print(f"[cyan]Key loaded: {len(key)} bytes")
        
        with open(crypt_path, 'rb') as f:
            data = f.read()
            
        console.print(f"[cyan]Database file size: {len(data)} bytes")
        
        if len(data) < 67:
            raise ValueError(f"File too small: {len(data)} bytes")
            
        # Crypt14 header is 67 bytes (IV is at offset 51-67)
        iv = data[51:67]
        encrypted = data[67:-16]  # Encrypted data without auth tag
        auth_tag = data[-16:]     # Last 16 bytes are the auth tag
            
        console.print(f"[cyan]IV length: {len(iv)}, Auth tag length: {len(auth_tag)}")
        
        # Create cipher with key and IV
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        
        # Decrypt without verification first
        decrypted = cipher.decrypt(encrypted)
        
        # Check if it looks like SQLite
        if not decrypted.startswith(b'SQLite format 3\x00'):
            raise ValueError("Not a valid SQLite database after decryption")
            
        # Write decrypted database
        with open(output_path, 'wb') as out:
            out.write(decrypted)
            
        console.print(f"[green]Successfully decrypted {len(decrypted)} bytes")
        return True
                
    except Exception as e:
        raise Exception(f"Decryption error: {str(e)}")

# === Convert Tables to Markdown ===
def export_all_tables_to_md(db_path, output_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    for table_name in tables:
        table_name = table_name[0]
        output_file = os.path.join(output_dir, f"{table_name}.md")
        rows = cursor.execute(f"SELECT * FROM {table_name}").fetchall()
        col_names = [desc[0] for desc in cursor.description]

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Table: {table_name}\n\n")
            f.write("| " + " | ".join(col_names) + " |\n")
            f.write("|" + " --- |" * len(col_names) + "\n")
            for row in rows:
                row_str = "| " + " | ".join([str(r) if r is not None else "" for r in row]) + " |\n"
                f.write(row_str)

    conn.close()

# === Main ===
def main():
    console.print("[bold blue]WhatsApp Decryption Tool Starting...\n")

    if not os.path.exists(KEY_PATH):
        console.print(f"[red]Key not found at {KEY_PATH}")
        return
    if not os.path.exists(CRYPT_FILE):
        console.print(f"[red]Crypt14 file not found at {CRYPT_FILE}")
        return

    decrypting_animation()

    try:
        decrypt_crypt14(KEY_PATH, CRYPT_FILE, OUTPUT_SQLITE)
        console.print(f"[green]✅ Decryption complete:\n{OUTPUT_SQLITE}")
    except Exception as e:
        console.print(f"[red]❌ Failed to decrypt: {e}")
        return

    try:
        export_all_tables_to_md(OUTPUT_SQLITE, OUTPUT_MD_DIR)
        console.print(f"[bold green]\n✅ All tables exported to Markdown in:\n{OUTPUT_MD_DIR}")
    except Exception as e:
        console.print(f"[red]❌ Failed to export Markdown: {e}")

if __name__ == "__main__":
    main()
