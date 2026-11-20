
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "instance" / "cashon.db"
STATIC = BASE / "app" / "static"

conn = sqlite3.connect(DB)
rows = conn.execute(
    "SELECT id, name, image FROM products ORDER BY id"
).fetchall()

print("\n========== CASHON IMAGE AUDIT ==========\n")

missing = []
remote = []
local_ok = []

for product_id, name, image in rows:
    if not image:
        missing.append((product_id, name, "EMPTY IMAGE"))
        continue

    if image.startswith(("http://", "https://")):
        remote.append((product_id, name, image))
        continue

    relative = image.replace("/static/", "", 1).lstrip("/")
    filepath = STATIC / relative

    if filepath.is_file():
        local_ok.append((product_id, name, image))
    else:
        missing.append((product_id, name, image))

print("WORKING LOCAL IMAGES:", len(local_ok))
print("EXTERNAL IMAGES TO VERIFY:", len(remote))
print("MISSING LOCAL IMAGES:", len(missing))

print("\n========== MISSING FILES ==========")
for item in missing:
    print(item)

print("\n========== EXTERNAL IMAGE URLS ==========")
for item in remote:
    print(item)

with open(BASE / "image_audit.txt", "w", encoding="utf-8") as f:
    f.write("MISSING LOCAL IMAGES\n")
    for item in missing:
        f.write(str(item) + "\n")

    f.write("\nEXTERNAL IMAGES\n")
    for item in remote:
        f.write(str(item) + "\n")

conn.close()
print("\nAudit complete! Check image_audit.txt")
