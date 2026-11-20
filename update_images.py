
import sqlite3
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "instance" / "cashon.db"
IMAGE_DIR = BASE / "app" / "static" / "img" / "products"

images = {
    1: "apple-laptop.png",
    3: "sony-headphones.png",
    50: "atomic-habits.png"
}

# Check images before updating database
for filename in images.values():
    if not (IMAGE_DIR / filename).exists():
        raise FileNotFoundError(f"Missing: {IMAGE_DIR / filename}")

# Backup database
shutil.copy2(DB, BASE / "cashon_backup.db")

conn = sqlite3.connect(DB)
cursor = conn.cursor()

for product_id, filename in images.items():
    url = f"/static/img/products/{filename}"

    cursor.execute(
        "UPDATE products SET image = ? WHERE id = ?",
        (url, product_id)
    )

    print(f"Updated product {product_id}: {filename}")

conn.commit()
conn.close()

print("SUCCESS! All three images connected.")
