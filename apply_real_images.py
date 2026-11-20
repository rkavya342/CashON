"""
apply_real_images.py — optional helper.

Put real product photos (jpg/png/webp) into app/static/img/products/ named
exactly  <product-slug>.<ext>  (for example  morphy-richards-kettle.jpg),
then run:   python apply_real_images.py
It points each matching product at its photo. Products without a file are
left unchanged. Nothing else in the database is touched.
"""
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / "instance" / "cashon.db"
IMG = BASE / "app" / "static" / "img" / "products"
NEEDS_PHOTO = ["morphy-richards-kettle", "nilkamal-floyd-sofa",
               "pepperfry-bookshelf-5tier", "titan-skywear-watch"]

conn = sqlite3.connect(DB)
for slug in NEEDS_PHOTO:
    for ext in ("jpg", "jpeg", "png", "webp"):
        if (IMG / f"{slug}.{ext}").exists():
            conn.execute("UPDATE products SET image=? WHERE slug=?",
                         (f"/static/img/products/{slug}.{ext}", slug))
            print("updated", slug)
            break
    else:
        print("no file yet for", slug)
conn.commit()
conn.close()
