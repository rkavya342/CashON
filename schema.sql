-- ============================================================
-- CASHON — Full Database Schema v2
-- Run with:  python seed.py
-- WARNING: DROP TABLE IF EXISTS wipes existing data on re-init
-- ============================================================

PRAGMA foreign_keys = OFF;

-- Drop all in reverse dependency order
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS security_events;
DROP TABLE IF EXISTS support_messages;
DROP TABLE IF EXISTS support_tickets;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS price_history;
DROP TABLE IF EXISTS search_history;
DROP TABLE IF EXISTS browsing_history;
DROP TABLE IF EXISTS refunds;
DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS wishlist;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS product_images;
DROP TABLE IF EXISTS product_specs;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS seller_profiles;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS coupons;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS users;

PRAGMA foreign_keys = ON;

-- ── Users ─────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE,
    name          TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'customer',
    -- role: 'customer' | 'seller' | 'admin'
    avatar        TEXT,
    phone         TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    email_verified INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Addresses ─────────────────────────────────────────────────────────────
CREATE TABLE addresses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label       TEXT    NOT NULL DEFAULT 'Home', -- Home, Work, Other
    full_name   TEXT    NOT NULL,
    phone       TEXT    NOT NULL,
    line1       TEXT    NOT NULL,
    line2       TEXT,
    city        TEXT    NOT NULL,
    state       TEXT    NOT NULL,
    pincode     TEXT    NOT NULL,
    country     TEXT    NOT NULL DEFAULT 'India',
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Seller Profiles ───────────────────────────────────────────────────────
CREATE TABLE seller_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    store_name      TEXT    NOT NULL,
    store_slug      TEXT    NOT NULL UNIQUE,
    description     TEXT,
    logo            TEXT,
    banner          TEXT,
    gst_number      TEXT,
    pan_number      TEXT,
    bank_account    TEXT,   -- encrypted / masked
    ifsc            TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    -- pending | verified | rejected | suspended
    verified_at     TEXT,
    total_sales     REAL    NOT NULL DEFAULT 0,
    total_orders    INTEGER NOT NULL DEFAULT 0,
    rating          REAL    NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Categories ────────────────────────────────────────────────────────────
CREATE TABLE categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    slug         TEXT    NOT NULL UNIQUE,
    description  TEXT,
    image        TEXT,
    icon         TEXT,       -- emoji or icon class
    theme_config TEXT,       -- JSON: {accent, bg, text, style}
    sort_order   INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1
);

-- ── Products ──────────────────────────────────────────────────────────────
CREATE TABLE products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL REFERENCES categories(id),
    seller_id    INTEGER REFERENCES seller_profiles(id),
    name         TEXT    NOT NULL,
    slug         TEXT    NOT NULL UNIQUE,
    description  TEXT,
    brand        TEXT,
    sku          TEXT    UNIQUE,
    price        REAL    NOT NULL,       -- MRP in INR
    sale_price   REAL,                  -- NULL = not on sale
    stock        INTEGER NOT NULL DEFAULT 0,
    rating       REAL    NOT NULL DEFAULT 0,
    review_count INTEGER NOT NULL DEFAULT 0,
    image        TEXT,                  -- primary image URL
    sizes        TEXT,                  -- JSON array
    colours      TEXT,                  -- JSON array
    tags         TEXT,                  -- JSON array for search
    is_featured  INTEGER NOT NULL DEFAULT 0,
    is_active    INTEGER NOT NULL DEFAULT 1,
    approval_status TEXT NOT NULL DEFAULT 'approved',
    -- pending | approved | rejected
    weight_grams INTEGER,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Product Images (gallery) ──────────────────────────────────────────────
CREATE TABLE product_images (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    url        TEXT    NOT NULL,
    alt        TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- ── Product Specifications ────────────────────────────────────────────────
CREATE TABLE product_specs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    spec_key   TEXT    NOT NULL,
    spec_value TEXT    NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- ── Reviews ───────────────────────────────────────────────────────────────
CREATE TABLE reviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    order_item_id   INTEGER,
    rating          INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    title           TEXT,
    body            TEXT    NOT NULL,
    is_verified     INTEGER NOT NULL DEFAULT 0,  -- purchased = verified
    helpful_count   INTEGER NOT NULL DEFAULT 0,
    is_approved     INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Wishlist ──────────────────────────────────────────────────────────────
CREATE TABLE wishlist (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    added_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, product_id)
);

-- ── Cart Items ────────────────────────────────────────────────────────────
CREATE TABLE cart_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    qty        INTEGER NOT NULL DEFAULT 1 CHECK(qty > 0),
    size       TEXT    NOT NULL DEFAULT '',
    colour     TEXT    NOT NULL DEFAULT '',
    added_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, product_id, size, colour)
);

-- ── Coupons ───────────────────────────────────────────────────────────────
CREATE TABLE coupons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT    NOT NULL UNIQUE,
    description TEXT,
    type        TEXT    NOT NULL DEFAULT 'percent',  -- 'percent' | 'fixed'
    value       REAL    NOT NULL,
    min_order   REAL    NOT NULL DEFAULT 0,
    max_discount REAL,                              -- cap for percent coupons
    uses_left   INTEGER NOT NULL DEFAULT -1,        -- -1 = unlimited
    used_count  INTEGER NOT NULL DEFAULT 0,
    expires_at  TEXT,
    is_active   INTEGER NOT NULL DEFAULT 1,
    seller_id   INTEGER REFERENCES seller_profiles(id),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Orders ────────────────────────────────────────────────────────────────
CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    order_number    TEXT    NOT NULL UNIQUE,  -- e.g. CASH20241101001
    total           REAL    NOT NULL,         -- final amount in INR
    subtotal        REAL    NOT NULL,
    discount        REAL    NOT NULL DEFAULT 0,
    shipping_fee    REAL    NOT NULL DEFAULT 0,
    tax             REAL    NOT NULL DEFAULT 0,
    status          TEXT    NOT NULL DEFAULT 'placed',
    -- placed | confirmed | packed | shipped | out_for_delivery | delivered | cancelled | return_requested | returned
    payment_status  TEXT    NOT NULL DEFAULT 'pending',
    -- pending | paid | failed | refunded | partially_refunded
    payment_method  TEXT    NOT NULL DEFAULT 'card',
    payment_ref     TEXT,   -- simulated transaction ID
    address_id      INTEGER REFERENCES addresses(id),
    address_snapshot TEXT   NOT NULL,  -- JSON snapshot of delivery address
    shipping_method TEXT    NOT NULL DEFAULT 'standard',
    coupon_id       INTEGER REFERENCES coupons(id),
    coupon_code     TEXT,
    notes           TEXT,
    estimated_delivery TEXT,
    delivered_at    TEXT,
    cancelled_at    TEXT,
    cancel_reason   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Order Items ───────────────────────────────────────────────────────────
CREATE TABLE order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    seller_id   INTEGER REFERENCES seller_profiles(id),
    name        TEXT    NOT NULL,  -- snapshot
    image       TEXT,
    qty         INTEGER NOT NULL,
    unit_price  REAL    NOT NULL,  -- INR at time of purchase
    size        TEXT,
    colour      TEXT,
    return_status TEXT  -- NULL | requested | approved | rejected | completed
);

-- ── Shipments ─────────────────────────────────────────────────────────────
CREATE TABLE shipments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    tracking_number TEXT,
    carrier         TEXT    NOT NULL DEFAULT 'BlueDart',
    status          TEXT    NOT NULL DEFAULT 'processing',
    shipped_at      TEXT,
    delivered_at    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Returns ───────────────────────────────────────────────────────────────
CREATE TABLE returns (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    order_item_id   INTEGER NOT NULL REFERENCES order_items(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    reason          TEXT    NOT NULL,
    description     TEXT,
    status          TEXT    NOT NULL DEFAULT 'requested',
    -- requested | approved | rejected | picked_up | refunded
    refund_amount   REAL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Refunds ───────────────────────────────────────────────────────────────
CREATE TABLE refunds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL REFERENCES orders(id),
    return_id       INTEGER REFERENCES returns(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    amount          REAL    NOT NULL,
    method          TEXT    NOT NULL DEFAULT 'original',  -- original | wallet | bank
    status          TEXT    NOT NULL DEFAULT 'pending',
    -- pending | processed | failed
    transaction_ref TEXT,
    processed_at    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Price History ─────────────────────────────────────────────────────────
CREATE TABLE price_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price       REAL    NOT NULL,
    sale_price  REAL,
    recorded_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Notifications ─────────────────────────────────────────────────────────
CREATE TABLE notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT    NOT NULL,
    -- order_update | price_drop | promotion | wishlist_alert | system
    title       TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    link        TEXT,
    is_read     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Search History ────────────────────────────────────────────────────────
CREATE TABLE search_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    query       TEXT    NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Browsing History ──────────────────────────────────────────────────────
CREATE TABLE browsing_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    viewed_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Support Tickets ───────────────────────────────────────────────────────
CREATE TABLE support_tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    order_id    INTEGER REFERENCES orders(id),
    subject     TEXT    NOT NULL,
    category    TEXT    NOT NULL DEFAULT 'general',
    -- general | order | payment | delivery | returns | product | account
    status      TEXT    NOT NULL DEFAULT 'open',
    -- open | in_progress | resolved | closed
    priority    TEXT    NOT NULL DEFAULT 'normal',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE support_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_id   INTEGER NOT NULL REFERENCES users(id),
    is_staff    INTEGER NOT NULL DEFAULT 0,
    message     TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Audit Logs ────────────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    action      TEXT    NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    details     TEXT,   -- JSON
    ip_address  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Security Events ───────────────────────────────────────────────────────
CREATE TABLE security_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT    NOT NULL,
    -- failed_login | suspicious_activity | rate_limit_exceeded | account_locked
    user_id     INTEGER REFERENCES users(id),
    ip_address  TEXT,
    details     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Indexes for performance ───────────────────────────────────────────────
CREATE INDEX idx_products_category  ON products(category_id);
CREATE INDEX idx_products_seller    ON products(seller_id);
CREATE INDEX idx_products_active    ON products(is_active);
CREATE INDEX idx_products_featured  ON products(is_featured);
CREATE INDEX idx_cart_user          ON cart_items(user_id);
CREATE INDEX idx_wishlist_user      ON wishlist(user_id);
CREATE INDEX idx_orders_user        ON orders(user_id);
CREATE INDEX idx_order_items_order  ON order_items(order_id);
CREATE INDEX idx_reviews_product    ON reviews(product_id);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_price_history_prod ON price_history(product_id, recorded_at);
CREATE INDEX idx_browsing_user      ON browsing_history(user_id, viewed_at);
