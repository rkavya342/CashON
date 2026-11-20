
import sqlite3
import urllib.request
import urllib.error
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "instance" / "cashon.db"

conn = sqlite3.connect(DB)

rows = conn.execute("""
    SELECT id, name, image
    FROM products
    WHERE image LIKE 'http%'
    ORDER BY id
""").fetchall()

print("\nCASHON EXTERNAL IMAGE CHECK\n")

for pid, name, url in rows:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="GET"
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            content_type = response.headers.get("Content-Type", "")
            if response.status == 200 and content_type.startswith("image/"):
                print(f"OK       | {pid} | {name}")
            else:
                print(f"CHECK    | {pid} | {name} | {content_type}")

    except Exception as e:
        print(f"FAILED   | {pid} | {name} | {e}")

conn.close()
