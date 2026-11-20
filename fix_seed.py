"""Fix emoji print statements in seed.py for Windows cp1252 compatibility."""
import pathlib, re

p = pathlib.Path("seed.py")
t = p.read_text(encoding="utf-8")

# Map each emoji-laden print to a plain ASCII equivalent
fixes = {
    '    print("🗑️  Dropping & recreating tables…")': '    print("Dropping & recreating tables...")',
    '    print("👤 Inserting users…")': '    print("Inserting users...")',
    '    print("📂 Inserting categories…")': '    print("Inserting categories...")',
    '    print("🛍️  Inserting 30 products…")': '    print("Inserting 30 products...")',
    '    print("🖼️  Inserting gallery images…")': '    print("Inserting gallery images...")',
    '    print("⭐ Inserting reviews…")': '    print("Inserting reviews...")',
    '    print("🎟️  Inserting coupons…")': '    print("Inserting coupons...")',
    '    print("📦 Inserting sample orders…")': '    print("Inserting sample orders...")',
    '    print("\\n✅ Done! Database seeded successfully.")': '    print("\\nDone! Database seeded successfully.")',
    '    print("\\n✅ Done! Database seeded successfully.")': '    print("\\nDone! Database seeded successfully.")',
}

for old, new in fixes.items():
    t = t.replace(old, new)

# Also replace any remaining non-ASCII in print statements
lines = t.split("\n")
clean = []
for line in lines:
    if "print(" in line and any(ord(c) > 127 for c in line):
        line = "".join(c if ord(c) < 128 else "" for c in line)
    clean.append(line)

t2 = "\n".join(clean)
p.write_text(t2, encoding="utf-8")
print("seed.py cleaned successfully.")
