import os
import sqlite3
import time
from tqdm import tqdm
from Crypto.Cipher import AES
from rich.console import Console

console = Console()

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(SCRIPT_DIR, "key")
CRYPT_FILE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt14"
OUTPUT_SQLITE = "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Databases/msgstore_decrypted.db"
OUTPUT_MD_DIR = os.path.expanduser("~/storage/shared/wadecryptor_output")

os.makedirs(OUTPUT_MD_DIR, exist_ok=True)

# === Terminal Animation ===
def decrypting_animation():
    with console.status("[bold green]Decrypting database..."):
        for _ in tqdm(range(30), desc="Decrypting", ncols=75):
            time.sleep(0.05)

# === AES Decryption Function ===
def decrypt_crypt14(key_file, crypt_file, output_file):
    try:
        with open(key_file, 'rb') as kf:
            key = kf.read()

        with open(crypt_file, 'rb') as f:
            data = f.read()

        iv = data[51:67]
        encrypted = data[67:]

        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        decrypted = cipher.decrypt(encrypted)

        with open(output_file, 'wb') as out:
            out.write(decrypted)
    except Exception as e:
        console.print(f"[red]❌ Decryption error: {str(e)}")
        raise

# === Convert Tables to Markdown ===
def export_all_tables_to_md(db_path, output_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    for table in tables:
        table_name = table[0]
        output_file = os.path.join(output_dir, f"{table_name}.md")
        rows = cursor.execute(f"SELECT * FROM {table_name}").fetchall()
        col_names = [desc[0] for desc in cursor.description]

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Table: {table_name}\n\n")
            f.write("| " + " | ".join(col_names) + " |\n")
            f.write("|" + " --- |" * len(col_names) + "\n")
            for row in rows:
                f.write("| " + " | ".join([str(r) if r is not None else "" for r in row]) + " |\n")

    conn.close()

# === Main ===
def main():
    console.print("[bold blue]🔓 WhatsApp Decryption Tool Starting...\n")

    if not os.path.exists(KEY_PATH):
        console.print(f"[red]❌ Key not found at: {KEY_PATH}")
        return
    if not os.path.exists(CRYPT_FILE):
        console.print(f"[red]❌ .crypt14 file not found at: {CRYPT_FILE}")
        return

    decrypting_animation()

    try:
        decrypt_crypt14(KEY_PATH, CRYPT_FILE, OUTPUT_SQLITE)
        console.print(f"[green]✅ Decryption complete: {OUTPUT_SQLITE}")
    except Exception as e:
        console.print(f"[red]❌ Failed to decrypt: {e}")
        return

    try:
        export_all_tables_to_md(OUTPUT_SQLITE, OUTPUT_MD_DIR)
        console.print(f"[bold green]📁 All tables exported to: {OUTPUT_MD_DIR}")
    except Exception as e:
        console.print(f"[red]❌ Failed to export Markdown: {e}")

if __name__ == "__main__":
    main()
