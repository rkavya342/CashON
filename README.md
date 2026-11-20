# CashOn — Fashion & Lifestyle Shop

A clean, modern e-commerce web app built with **Flask + SQLite + Bootstrap 5**.

---

## Quick Start

```bash
# 1. Install dependencies (Python 3.11+ required)
pip install -r requirements.txt

# 2. Seed the database with sample data
python seed.py

# 3. Run the app
python run.py
```

Open **http://localhost:5000** in your browser.

---

## Seeded Accounts

| Role     | Email                     | Password      |
|----------|---------------------------|---------------|
| Admin    | admin@cashon.local        | Admin@1234    |
| Customer | alice@example.com         | Password1!    |
| Customer | bob@example.com           | Password1!    |
| Customer | carol@example.com         | Password1!    |

---

## Project Structure

```
cashon/
├── app/
│   ├── __init__.py          # App factory
│   ├── db.py                # SQLite helpers (get_db, init_db)
│   ├── auth/                # Authentication blueprint
│   ├── shop/                # Shop & public pages blueprint
│   ├── orders/              # Orders blueprint
│   ├── admin/               # Admin panel blueprint
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html        # Master layout (navbar, footer, cart drawer)
│   │   ├── shop/            # Homepage, listing, product, cart, checkout …
│   │   ├── auth/            # Login, register, profile, wishlist …
│   │   ├── orders/          # Order list, detail, tracking …
│   │   ├── admin/           # Dashboard, products, orders, customers …
│   │   └── errors/          # 404, 500, 403
│   └── static/
│       ├── css/main.css     # Full design system (tokens, components, animations)
│       ├── js/main.js       # Cart drawer, search, toasts, tilt, glow …
│       └── img/             # Product photos, category tiles, banners
├── uploads/                 # User-uploaded avatars and product images
├── schema.sql               # Database schema (all tables)
├── seed.py                  # Database seeder (sample data + images)
├── run.py                   # Entry point — `python run.py`
└── requirements.txt
```

---

## Design System

| Token          | Value       | Usage                            |
|----------------|-------------|----------------------------------|
| `--cream`      | `#FFF6D6`   | Page background                  |
| `--cream-deep` | `#FFEDB0`   | Section backgrounds, hover       |
| `--white`      | `#FFFFFF`   | Cards, inputs                    |
| `--burgundy`   | `#5E1A2E`   | Headings, text, footer           |
| `--blush`      | `#F1C5C9`   | Soft cards, banners              |
| `--chartreuse` | `#C8E61C`   | Sale badges, focus rings, pops   |
| `--royal`      | `#2563EB`   | Links, info accents              |

Fonts: **Fraunces** (display headings) + **Inter** (body text)

---

## Build Phases

| Phase | Contents                                              | Status    |
|-------|-------------------------------------------------------|-----------|
| 1     | Scaffold, design system CSS, navbar, footer, routes   | ✅ Done   |
| 2     | Database, seed data with real images, homepage        | 🔜 Next   |
| 3     | Shop listing, filters, product page, reviews          | —         |
| 4     | Cart, coupons, checkout, orders, wishlist, compare    | —         |
| 5     | Accounts (full), admin panel                          | —         |
| 6     | Animation polish, responsive, accessibility pass      | —         |
| 7     | End-to-end testing, bug fixes, final README           | —         |
