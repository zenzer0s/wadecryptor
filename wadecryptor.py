import os
import sqlite3
import time
from tqdm import tqdm
from Crypto.Cipher import AES
from rich.console import Console
import zlib
import binascii
import struct

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
            return raw[-32:]  # Take first 32 bytes instead of last 32
        else:
            raise ValueError(f"Key file too small: {len(raw)} bytes")

# === Process decrypted data function ===
def process_decrypted_data(decrypted_data, output_path):
    """Process potentially compressed or encoded data after decryption"""
    try:
        # Check if data is a SQLite database
        if decrypted_data.startswith(b'SQLite format 3\x00'):
            console.print("[green]Detected SQLite format - no additional processing needed")
            with open(output_path, 'wb') as out:
                out.write(decrypted_data)
            return True
            
        # Try to decompress with zlib (common compression method)
        console.print("[yellow]Attempting zlib decompression...")
        try:
            decompressed = zlib.decompress(decrypted_data)
            if decompressed.startswith(b'SQLite format 3\x00'):
                console.print("[green]Successfully decompressed zlib data to SQLite")
                with open(output_path, 'wb') as out:
                    out.write(decompressed)
                return True
        except Exception as e:
            console.print(f"[yellow]Not zlib compressed: {e}")
            
        # Try LZ4 compression (used by some newer WhatsApp versions)
        console.print("[yellow]Attempting LZ4 decompression...")
        try:
            # Try to import lz4.frame - pip install lz4
            import lz4.frame
            decompressed = lz4.frame.decompress(decrypted_data)
            if decompressed.startswith(b'SQLite format 3\x00'):
                console.print("[green]Successfully decompressed LZ4 data to SQLite")
                with open(output_path, 'wb') as out:
                    out.write(decompressed)
                return True
        except ImportError:
            console.print("[yellow]LZ4 library not installed. Run 'pip install lz4' to enable LZ4 support")
        except Exception as e:
            console.print(f"[yellow]Not LZ4 compressed: {e}")
        
        # Try to identify the format from the first bytes
        header_hex = binascii.hexlify(decrypted_data[:16]).decode()
        console.print(f"[yellow]Unknown format with header: {header_hex}")
        
        # Save the raw decrypted data for manual analysis
        raw_output = output_path + ".raw"
        with open(raw_output, 'wb') as out:
            out.write(decrypted_data)
        console.print(f"[yellow]Saved raw decrypted data to: {raw_output}")
        
        # Create a more detailed hex viewer output
        hex_output = output_path + ".hex"
        with open(hex_output, 'w') as out:
            # Write header
            out.write("Decrypted WhatsApp Database Hex Dump\n")
            out.write("=====================================\n\n")
            
            # Write first 2048 bytes as hex dump for more context
            for i in range(0, min(2048, len(decrypted_data)), 16):
                line = decrypted_data[i:i+16]
                hex_line = ' '.join(f'{b:02x}' for b in line)
                ascii_line = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in line)
                out.write(f"{i:08x}: {hex_line:<48} |{ascii_line}|\n")
        
        console.print(f"[yellow]Saved detailed hex dump to: {hex_output}")
        console.print("[yellow]To install LZ4 support: run 'pip install lz4' and try again")
        return False
        
    except Exception as e:
        console.print(f"[red]Error processing decrypted data: {e}")
        return False

# === AES Decryption Function ===
def decrypt_crypt14(key_path, crypt_path, output_path):
    try:
        # Load key
        key = load_key(key_path)
        console.print(f"[cyan]Key loaded: {len(key)} bytes")
        
        # Read encrypted database
        with open(crypt_path, 'rb') as f:
            data = f.read()
        
        console.print(f"[cyan]Database file size: {len(data)} bytes")
        
        # Header analysis
        file_magic = data[:8]
        console.print(f"[cyan]File magic: {file_magic.hex()}")
        
        # Modern WhatsApp databases are not raw SQLite
        console.print("[cyan]Detected newer WhatsApp database format...")
        
        # Try Google Protobuf approach
        if file_magic.startswith(b'\xbf\x01'):
            console.print("[yellow]Trying protobuf-based format...")
            
            # New config specifically for 2023+ WhatsApp formats
            # Header is now 141 bytes, IV at offset 123
            header_size = 141
            iv_start = 123
            iv_length = 16
            
            if len(data) < header_size + 32:
                raise ValueError("File too small for protobuf format")
            
            # Extract IV
            iv = data[iv_start:iv_start+iv_length]
            console.print(f"[cyan]IV bytes: {iv.hex()}")
            
            # Get encrypted data
            encrypted = data[header_size:-16]
            auth_tag = data[-16:]
            
            # Try decryption
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            try:
                # Decrypt without auth tag validation
                decrypted = cipher.decrypt(encrypted)
                
                console.print(f"[green]✅ Successfully decrypted {len(decrypted)} bytes")
                console.print(f"[cyan]First 32 bytes: {decrypted[:32].hex()}")
                
                # Process the decrypted data
                success = process_decrypted_data(decrypted, output_path)
                if not success:
                    console.print("[yellow]Warning: Data was decrypted but isn't a standard SQLite database")
                
                # Return even if not valid SQLite - might be another format
                return True
                
            except Exception as e:
                raise ValueError(f"Protobuf format decryption failed: {str(e)}")
        
        # If we get here, fall back to the old approach with multiple configs
        success = False
        
        # Try different offsets for IV and auth tag
        possible_configs = [
            # Add more configs including some for newer formats
            (141, 123, 16, True),  # Newer WhatsApp (2023+)
            (67, 51, 16, True),    # Standard crypt14
            (67, 51, 16, False),   # crypt14 without auth_tag
            (158, 130, 12, True),  # Very new format (experimental)
            (164, 152, 12, True),  # Another possible new format
        ]
        
        for config in possible_configs:
            header_size, iv_start, iv_length, has_auth_tag = config
            
            console.print(f"[yellow]Trying config: header={header_size}, iv_start={iv_start}")
            
            # Check if file is large enough
            if len(data) < header_size + iv_length + 16:
                console.print("[yellow]File too small for this config, skipping")
                continue
                
            # Extract IV
            iv = data[iv_start:iv_start+iv_length]
            
            # Get encrypted data and auth tag
            if has_auth_tag:
                encrypted = data[header_size:-16]
                auth_tag = data[-16:]
            else:
                encrypted = data[header_size:]
                auth_tag = None
                
            # Try decryption
            cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
            try:
                # Decrypt without auth tag verification
                decrypted = cipher.decrypt(encrypted)
                
                # Save the result
                with open(output_path, 'wb') as out:
                    out.write(decrypted)
                
                # Check if it looks like SQLite
                if decrypted.startswith(b'SQLite format 3\x00'):
                    console.print(f"[green]✅ Successfully decrypted with config {config}")
                    success = True
                    break
                else:
                    console.print(f"[yellow]⚠️ Decryption produced non-SQLite data with config {config}")
                    console.print(f"[yellow]First 16 bytes: {decrypted[:16].hex()}")
            
            except Exception as e:
                console.print(f"[yellow]Failed with config {config}: {str(e)}")
                continue
        
        if not success:
            raise ValueError("Failed to decrypt database with any config")
            
        return True
                
    except Exception as e:
        raise Exception(f"Decryption error: {str(e)}")

# === Convert Tables to Markdown ===
def export_all_tables_to_md(db_path, output_dir):
    try:
        # First test if this is even a valid SQLite database
        if not os.path.exists(db_path):
            raise ValueError(f"Database file not found: {db_path}")
            
        with open(db_path, 'rb') as f:
            header = f.read(16)
            if not header.startswith(b'SQLite format 3\x00'):
                raise ValueError("File is not a standard SQLite database")
        
        # Continue with export if it's a valid SQLite file
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
    
    except Exception as e:
        raise ValueError(f"File is not a database: {str(e)}")

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
        success = decrypt_crypt14(KEY_PATH, CRYPT_FILE, OUTPUT_SQLITE)
        console.print(f"[green]✅ Decryption complete:\n{OUTPUT_SQLITE}")
        
        # Only try to export if the output is a SQLite database
        if os.path.exists(OUTPUT_SQLITE):
            with open(OUTPUT_SQLITE, 'rb') as f:
                if f.read(16).startswith(b'SQLite format 3\x00'):
                    try:
                        export_all_tables_to_md(OUTPUT_SQLITE, OUTPUT_MD_DIR)
                        console.print(f"[bold green]\n✅ All tables exported to Markdown in:\n{OUTPUT_MD_DIR}")
                    except Exception as e:
                        console.print(f"[red]❌ Failed to export Markdown: {e}")
                else:
                    console.print("[yellow]⚠️ Skipping Markdown export - decrypted file is not a SQLite database")
                    console.print("[yellow]Check the .raw and .hex files for further analysis")
    except Exception as e:
        console.print(f"[red]❌ Failed to decrypt: {e}")
        return

if __name__ == "__main__":
    main()
