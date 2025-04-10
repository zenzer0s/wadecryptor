import os
import sqlite3
import time
from tqdm import tqdm
from Crypto.Cipher import AES
from rich.console import Console

console = Console()

# === Paths ===
KEY_PATH = "/storage/emulated/0/Android/data/com.whatsapp/files/key"
CRYPT_FILE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt14"
OUTPUT_SQLITE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore_decrypted.db"
OUTPUT_MD_DIR = "/storage/emulated/0/markdown"

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
        return raw[-32:]  # Ensure correct 256-bit AES key

# === AES Decryption Function ===
def decrypt_crypt14(key_path, crypt_path, output_path):
    key = load_key(key_path)

    with open(crypt_path, 'rb') as f:
        data = f.read()

    iv = data[51:67]                    # 16 bytes IV
    encrypted = data[67:-16]            # Everything except the last 16 bytes
    auth_tag = data[-16:]               # Last 16 bytes = auth tag

    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    try:
        decrypted = cipher.decrypt_and_verify(encrypted, auth_tag)
    except ValueError as e:
        raise Exception("Authentication failed: " + str(e))

    with open(output_path, 'wb') as out:
        out.write(decrypted)

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
