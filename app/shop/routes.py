"""
app/shop/routes.py — Full CASHON Shop Routes v2
Includes: homepage, listing, product detail, cart, wishlist,
          checkout redirect, search API, cart contents API,
          AI assistant API, price history API, notifications API
Currency: INR (Indian Rupees)
"""

import json
import re
from flask import render_template, jsonify, request, session, redirect, url_for
from app.db import get_db
from . import shop_bp


# ── Helpers ───────────────────────────────────────────────────────────────────

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def inr(amount):
    """Format amount as INR string."""
    if amount is None:
        return None
    return f"\u20b9{amount:,.0f}"


# ── Homepage ─────────────────────────────────────────────────────────────────

@shop_bp.route("/")
def index():
    db = get_db()

    categories = rows_to_list(db.execute(
        "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
    ).fetchall())

    # Parse theme_config JSON for each category
    for cat in categories:
        try:
            cat["theme"] = json.loads(cat.get("theme_config") or "{}")
        except (json.JSONDecodeError, TypeError):
            cat["theme"] = {}

    new_arrivals = rows_to_list(db.execute(
        """SELECT p.*, c.name as cat_name, c.slug as cat_slug
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.is_active=1 AND p.approval_status='approved'
           ORDER BY p.created_at DESC LIMIT 8"""
    ).fetchall())

    best_sellers = rows_to_list(db.execute(
        """SELECT p.*, c.name as cat_name, c.slug as cat_slug
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.is_active=1 AND p.approval_status='approved'
           ORDER BY p.rating DESC, p.review_count DESC LIMIT 8"""
    ).fetchall())

    on_sale = rows_to_list(db.execute(
        """SELECT p.*, c.name as cat_name, c.slug as cat_slug
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.is_active=1 AND p.approval_status='approved'
             AND p.sale_price IS NOT NULL
           ORDER BY (p.price - p.sale_price) DESC LIMIT 6"""
    ).fetchall())

    testimonials = rows_to_list(db.execute(
        """SELECT r.*, u.name as user_name, u.avatar as user_avatar,
                  p.name as product_name
           FROM reviews r
           JOIN users u ON r.user_id=u.id
           JOIN products p ON r.product_id=p.id
           WHERE r.rating=5 AND r.is_approved=1
           ORDER BY r.created_at DESC LIMIT 3"""
    ).fetchall())

    # Personalized section
    picked_for_you = []
    if "user_id" in session:
        past_cats = db.execute(
            """SELECT DISTINCT p.category_id
               FROM order_items oi
               JOIN orders o ON oi.order_id=o.id
               JOIN products p ON oi.product_id=p.id
               WHERE o.user_id=?""",
            (session["user_id"],)
        ).fetchall()

        if past_cats:
            cat_ids = tuple(r["category_id"] for r in past_cats)
            placeholders = ",".join("?" * len(cat_ids))
            picked_for_you = rows_to_list(db.execute(
                f"""SELECT p.*, c.name as cat_name, c.slug as cat_slug
                    FROM products p JOIN categories c ON p.category_id=c.id
                    WHERE p.is_active=1 AND p.category_id IN ({placeholders})
                      AND p.id NOT IN (
                          SELECT oi.product_id FROM order_items oi
                          JOIN orders o ON oi.order_id=o.id WHERE o.user_id=?)
                    ORDER BY p.rating DESC LIMIT 6""",
                cat_ids + (session["user_id"],)
            ).fetchall())

        if not picked_for_you:
            # Fallback: browsing history based
            browsed = db.execute(
                """SELECT DISTINCT product_id FROM browsing_history
                   WHERE user_id=? ORDER BY viewed_at DESC LIMIT 10""",
                (session["user_id"],)
            ).fetchall()
            if browsed:
                pids = tuple(r["product_id"] for r in browsed)
                placeholders = ",".join("?" * len(pids))
                picked_for_you = rows_to_list(db.execute(
                    f"""SELECT p.*, c.name as cat_name FROM products p
                        JOIN categories c ON p.category_id=c.id
                        WHERE p.id IN ({placeholders}) AND p.is_active=1
                        ORDER BY p.rating DESC LIMIT 6""",
                    pids
                ).fetchall())

        if not picked_for_you:
            picked_for_you = rows_to_list(db.execute(
                """SELECT p.*, c.name as cat_name, c.slug as cat_slug
                   FROM products p JOIN categories c ON p.category_id=c.id
                   WHERE p.is_active=1 AND p.is_featured=1
                   ORDER BY p.rating DESC LIMIT 6"""
            ).fetchall())

    return render_template(
        "shop/index.html",
        categories=categories,
        new_arrivals=new_arrivals,
        best_sellers=best_sellers,
        on_sale=on_sale,
        testimonials=testimonials,
        picked_for_you=picked_for_you,
    )


# ── Shop Listing ─────────────────────────────────────────────────────────────

@shop_bp.route("/shop")
def listing():
    db = get_db()

    cat_slug = request.args.get("category", "")
    sort     = request.args.get("sort", "newest")
    min_p    = request.args.get("min_price", 0, type=float)
    max_p    = request.args.get("max_price", 999999, type=float)
    sale     = request.args.get("sale", 0, type=int)
    brand_f  = request.args.get("brand", "")
    page     = request.args.get("page", 1, type=int)
    q        = request.args.get("q", "").strip()
    per_page = 12

    where_parts = ["p.is_active=1", "p.approval_status='approved'", "p.price BETWEEN ? AND ?"]
    params      = [min_p, max_p]

    if cat_slug:
        where_parts.append("c.slug=?")
        params.append(cat_slug)
    if sale:
        where_parts.append("p.sale_price IS NOT NULL")
    if brand_f:
        where_parts.append("p.brand=?")
        params.append(brand_f)
    if q:
        where_parts.append("(p.name LIKE ? OR p.description LIKE ? OR p.brand LIKE ? OR p.tags LIKE ?)")
        params.extend([f"%{q}%"] * 4)

    sort_map = {
        "newest":    "p.created_at DESC",
        "popular":   "p.rating DESC, p.review_count DESC",
        "price_asc": "COALESCE(p.sale_price,p.price) ASC",
        "price_desc":"COALESCE(p.sale_price,p.price) DESC",
        "rating":    "p.rating DESC",
    }
    order_by = sort_map.get(sort, "p.created_at DESC")
    where_sql = " AND ".join(where_parts)

    total_count = db.execute(
        f"SELECT COUNT(*) FROM products p JOIN categories c ON p.category_id=c.id WHERE {where_sql}",
        params
    ).fetchone()[0]

    products = rows_to_list(db.execute(
        f"""SELECT p.*, c.name as cat_name, c.slug as cat_slug
            FROM products p JOIN categories c ON p.category_id=c.id
            WHERE {where_sql} ORDER BY {order_by}
            LIMIT ? OFFSET ?""",
        params + [per_page, (page-1)*per_page]
    ).fetchall())

    categories = rows_to_list(db.execute(
        "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
    ).fetchall())

    # Parse themes
    for cat in categories:
        try:
            cat["theme"] = json.loads(cat.get("theme_config") or "{}")
        except (json.JSONDecodeError, TypeError):
            cat["theme"] = {}

    # Active category info + theme
    active_cat = None
    active_theme = None
    if cat_slug:
        active_cat = next((c for c in categories if c["slug"] == cat_slug), None)
        if active_cat:
            active_theme = active_cat.get("theme")

    # Available brands for filter
    brands = rows_to_list(db.execute(
        """SELECT DISTINCT p.brand, COUNT(*) as cnt
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.is_active=1 AND p.brand IS NOT NULL
           """ + ("AND c.slug=?" if cat_slug else "") + """
           GROUP BY p.brand ORDER BY cnt DESC LIMIT 20""",
        ([cat_slug] if cat_slug else [])
    ).fetchall())

    # Min/max price range for the filter
    price_bounds = db.execute(
        """SELECT MIN(COALESCE(sale_price,price)), MAX(price)
           FROM products WHERE is_active=1"""
    ).fetchone()
    abs_min = int(price_bounds[0] or 0)
    abs_max = int(price_bounds[1] or 999999)

    total_pages = (total_count + per_page - 1) // per_page

    # Save search query to history
    if q and "user_id" in session:
        try:
            db.execute(
                "INSERT INTO search_history (user_id,query,result_count) VALUES (?,?,?)",
                (session["user_id"], q, total_count)
            )
            db.commit()
        except Exception:
            pass

    return render_template(
        "shop/listing.html",
        products=products,
        categories=categories,
        active_cat=active_cat,
        active_theme=active_theme,
        brands=brands,
        total_count=total_count,
        total_pages=total_pages,
        current_page=page,
        current_cat=cat_slug,
        current_sort=sort,
        current_brand=brand_f,
        min_price=min_p,
        max_price=max_p if max_p < 999999 else "",
        abs_min=abs_min,
        abs_max=abs_max,
        sale_only=sale,
        search_query=q,
        per_page=per_page,
    )


# ── Product Detail ────────────────────────────────────────────────────────────

@shop_bp.route("/product/<slug>")
def product(slug):
    db = get_db()

    prod = row_to_dict(db.execute(
        """SELECT p.*, c.name as cat_name, c.slug as cat_slug,
                  c.theme_config as cat_theme_config
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.slug=? AND p.is_active=1""",
        (slug,)
    ).fetchone())

    if not prod:
        return render_template("errors/404.html"), 404

    images = rows_to_list(db.execute(
        "SELECT * FROM product_images WHERE product_id=? ORDER BY sort_order",
        (prod["id"],)
    ).fetchall())

    specs = rows_to_list(db.execute(
        "SELECT * FROM product_specs WHERE product_id=? ORDER BY sort_order",
        (prod["id"],)
    ).fetchall())

    reviews = rows_to_list(db.execute(
        """SELECT r.*, u.name as user_name FROM reviews r
           JOIN users u ON r.user_id=u.id
           WHERE r.product_id=? AND r.is_approved=1
           ORDER BY r.created_at DESC""",
        (prod["id"],)
    ).fetchall())

    related = rows_to_list(db.execute(
        """SELECT p.*, c.name as cat_name FROM products p
           JOIN categories c ON p.category_id=c.id
           WHERE p.category_id=? AND p.id!=? AND p.is_active=1
           ORDER BY p.rating DESC LIMIT 4""",
        (prod["category_id"], prod["id"])
    ).fetchall())

    # Price history (last 30 days)
    price_history = rows_to_list(db.execute(
        """SELECT price, sale_price, recorded_at
           FROM price_history WHERE product_id=?
           ORDER BY recorded_at ASC LIMIT 30""",
        (prod["id"],)
    ).fetchall())

    # In wishlist?
    in_wishlist = False
    if "user_id" in session:
        wl = db.execute(
            "SELECT id FROM wishlist WHERE user_id=? AND product_id=?",
            (session["user_id"], prod["id"])
        ).fetchone()
        in_wishlist = bool(wl)

    # Parse JSON arrays
    try:
        prod["sizes_list"]   = json.loads(prod.get("sizes")   or "[]")
        prod["colours_list"] = json.loads(prod.get("colours") or "[]")
        prod["tags_list"]    = json.loads(prod.get("tags")    or "[]")
    except (json.JSONDecodeError, TypeError):
        prod["sizes_list"] = prod["colours_list"] = prod["tags_list"] = []

    # Give non-colour variants an accurate label instead of calling every option a colour.
    option_labels = {
        "tommy-hilfiger-impact": "Size",
        "boldfit-whey-protein-1kg": "Flavour",
        "prestige-incense-sticks-set": "Fragrance",
        "lakme-9to5-lipstick": "Shade",
    }
    prod["variant_label"] = option_labels.get(prod.get("slug"), "Colour")
    prod["variant_is_colour"] = prod["variant_label"] == "Colour"

    # Parse category theme
    try:
        prod["cat_theme"] = json.loads(prod.get("cat_theme_config") or "{}")
    except (json.JSONDecodeError, TypeError):
        prod["cat_theme"] = {}

    # Rating breakdown
    rating_breakdown = {}
    for star in range(1, 6):
        count = db.execute(
            "SELECT COUNT(*) FROM reviews WHERE product_id=? AND rating=?",
            (prod["id"], star)
        ).fetchone()[0]
        rating_breakdown[star] = count

    # Track in browsing history
    if "user_id" in session:
        try:
            db.execute(
                """INSERT OR IGNORE INTO browsing_history (user_id,product_id) VALUES (?,?)""",
                (session["user_id"], prod["id"])
            )
            db.commit()
        except Exception:
            pass

    # Track recently viewed in session
    rv = session.get("recently_viewed", [])
    if slug not in rv:
        rv.insert(0, slug)
        session["recently_viewed"] = rv[:8]

    return render_template(
        "shop/product.html",
        product=prod,
        images=images,
        specs=specs,
        reviews=reviews,
        related=related,
        price_history=price_history,
        in_wishlist=in_wishlist,
        rating_breakdown=rating_breakdown,
    )


# ── Static pages ──────────────────────────────────────────────────────────────

@shop_bp.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect(url_for("auth.login", next="/cart"))

    db = get_db()
    items = rows_to_list(db.execute(
        """SELECT ci.*, p.name, p.slug, p.image, p.stock,
                  COALESCE(p.sale_price, p.price) as unit_price,
                  p.price as original_price, p.sale_price
           FROM cart_items ci
           JOIN products p ON ci.product_id=p.id
           WHERE ci.user_id=?
           ORDER BY ci.added_at DESC""",
        (session["user_id"],)
    ).fetchall())

    subtotal = sum(item["unit_price"] * item["qty"] for item in items)
    shipping = 0 if subtotal >= 499 else 99
    total = subtotal + shipping

    coupons = rows_to_list(db.execute(
        "SELECT code, description, type, value, min_order FROM coupons WHERE is_active=1 ORDER BY value DESC LIMIT 5"
    ).fetchall())

    return render_template(
        "shop/cart.html",
        items=items,
        subtotal=subtotal,
        shipping=shipping,
        total=total,
        coupons=coupons,
    )

@shop_bp.route("/about")
def about():
    return render_template("shop/about.html")

@shop_bp.route("/contact")
def contact():
    return render_template("shop/contact.html")

@shop_bp.route("/faq")
def faq():
    return render_template("shop/faq.html")


# ══════════════════════════════════════════════════════════════════════════════
# JSON APIs
# ══════════════════════════════════════════════════════════════════════════════

@shop_bp.route("/api/search")
def api_search():
    """Live search — returns top 8 matching products."""
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"products": []})

    db = get_db()
    rows = db.execute(
        """SELECT p.slug, p.name, p.price, p.sale_price, p.image, p.rating,
                  c.name as category
           FROM products p JOIN categories c ON p.category_id=c.id
           WHERE p.is_active=1
             AND (p.name LIKE ? OR p.description LIKE ? OR p.brand LIKE ? OR p.tags LIKE ?)
           ORDER BY p.rating DESC, p.review_count DESC
           LIMIT 8""",
        (f"%{q}%",) * 4
    ).fetchall()

    return jsonify({"products": [dict(r) for r in rows]})


@shop_bp.route("/api/cart/contents")
def api_cart_contents():
    """Return cart items + total for the drawer."""
    if "user_id" not in session:
        return jsonify({"items": [], "total": 0, "count": 0})

    db = get_db()
    rows = db.execute(
        """SELECT ci.id, ci.qty, ci.size, ci.colour,
                  p.name, p.image, p.slug,
                  COALESCE(p.sale_price, p.price) as unit_price
           FROM cart_items ci
           JOIN products p ON ci.product_id=p.id
           WHERE ci.user_id=?
           ORDER BY ci.added_at DESC""",
        (session["user_id"],)
    ).fetchall()

    items = [dict(r) for r in rows]
    total = sum(item["unit_price"] * item["qty"] for item in items)
    count = sum(item["qty"] for item in items)
    return jsonify({"items": items, "total": int(total), "count": count})


@shop_bp.route("/api/cart/count")
def api_cart_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(qty),0) as cnt FROM cart_items WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()
    return jsonify({"count": row["cnt"] if row else 0})


@shop_bp.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    if "user_id" not in session:
        return jsonify({"ok": False, "login_required": True,
                        "message": "Please sign in to add items."}), 401

    data       = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    qty        = max(1, int(data.get("qty", 1)))
    size       = data.get("size", "")
    colour     = data.get("colour", "")

    if not product_id:
        return jsonify({"ok": False, "message": "No product specified."}), 400

    db = get_db()
    prod = db.execute(
        "SELECT id, name, stock FROM products WHERE id=? AND is_active=1",
        (product_id,)
    ).fetchone()

    if not prod:
        return jsonify({"ok": False, "message": "Product not found."}), 404
    if prod["stock"] < qty:
        return jsonify({"ok": False, "message": "Insufficient stock."}), 400

    try:
        db.execute(
            """INSERT INTO cart_items (user_id,product_id,qty,size,colour)
               VALUES (?,?,?,?,?)
               ON CONFLICT(user_id,product_id,size,colour)
               DO UPDATE SET qty=qty+excluded.qty""",
            (session["user_id"], product_id, qty, size or "", colour or "")
        )
        db.commit()
    except Exception as ex:
        return jsonify({"ok": False, "message": str(ex)}), 500

    count_row = db.execute(
        "SELECT COALESCE(SUM(qty),0) as cnt FROM cart_items WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    return jsonify({
        "ok": True,
        "count": count_row["cnt"] if count_row else 0,
        "message": f"{prod['name']} added to cart!",
    })


@shop_bp.route("/api/cart/update", methods=["POST"])
def api_cart_update():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    data    = request.get_json(silent=True) or {}
    item_id = data.get("item_id")
    qty     = max(0, int(data.get("qty", 1)))
    db      = get_db()
    if qty == 0:
        db.execute("DELETE FROM cart_items WHERE id=? AND user_id=?",
                   (item_id, session["user_id"]))
    else:
        db.execute("UPDATE cart_items SET qty=? WHERE id=? AND user_id=?",
                   (qty, item_id, session["user_id"]))
    db.commit()
    return jsonify({"ok": True})


@shop_bp.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    data    = request.get_json(silent=True) or {}
    item_id = data.get("item_id")
    db      = get_db()
    db.execute("DELETE FROM cart_items WHERE id=? AND user_id=?",
               (item_id, session["user_id"]))
    db.commit()
    return jsonify({"ok": True})


@shop_bp.route("/api/wishlist/toggle", methods=["POST"])
def api_wishlist_toggle():
    if "user_id" not in session:
        return jsonify({"ok": False, "login_required": True}), 401

    data       = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    db         = get_db()

    existing = db.execute(
        "SELECT id FROM wishlist WHERE user_id=? AND product_id=?",
        (session["user_id"], product_id)
    ).fetchone()

    if existing:
        db.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?",
                   (session["user_id"], product_id))
        in_wishlist = False
    else:
        db.execute(
            "INSERT OR IGNORE INTO wishlist (user_id,product_id) VALUES (?,?)",
            (session["user_id"], product_id)
        )
        in_wishlist = True

    db.commit()
    return jsonify({"ok": True, "in_wishlist": in_wishlist})


@shop_bp.route("/api/price-history/<int:product_id>")
def api_price_history(product_id):
    db = get_db()
    rows = db.execute(
        """SELECT price, sale_price, recorded_at
           FROM price_history WHERE product_id=?
           ORDER BY recorded_at ASC LIMIT 30""",
        (product_id,)
    ).fetchall()
    return jsonify({"history": [dict(r) for r in rows]})


@shop_bp.route("/api/notifications/count")
def api_notif_count():
    if "user_id" not in session:
        return jsonify({"count": 0})
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as cnt FROM notifications WHERE user_id=? AND is_read=0",
        (session["user_id"],)
    ).fetchone()
    return jsonify({"count": row["cnt"] if row else 0})


# ── AI Shopping Assistant ─────────────────────────────────────────────────────

@shop_bp.route("/api/assistant", methods=["POST"])
def api_assistant():
    """
    Rule-based intelligent shopping assistant.
    Understands: budgets (INR), categories, use-cases, brands, comparisons.
    Returns: response text + matching products from DB.
    """
    data  = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"response": "Please tell me what you're looking for!", "products": []})

    db = get_db()
    q_lower = query.lower()

    # ── 1. Extract budget ────────────────────────────────────────────
    budget = None
    budget_patterns = [
        r'under\s*[₹rs\.]*\s*([\d,]+)',
        r'below\s*[₹rs\.]*\s*([\d,]+)',
        r'less\s+than\s*[₹rs\.]*\s*([\d,]+)',
        r'budget\s+(?:of|is|around)?\s*[₹rs\.]*\s*([\d,]+)',
        r'[₹rs\.]+\s*([\d,]+)',
        r'([\d,]+)\s*(?:rupees?|inr|rs)',
        r'([\d,]+)k\b',
    ]
    for pattern in budget_patterns:
        m = re.search(pattern, q_lower)
        if m:
            num_str = m.group(1).replace(",", "")
            budget = float(num_str)
            if 'k' in pattern and budget < 1000:
                budget *= 1000
            break

    # ── 2. Detect category ───────────────────────────────────────────
    cat_map = {
        "technology":    ["laptop","phone","smartphone","tablet","ipad","macbook","earphone",
                          "headphone","watch","smartwatch","charger","keyboard","mouse","monitor",
                          "gaming","tech","gadget","electronic","computer","wireless"],
        "furniture-home":["sofa","furniture","bed","chair","table","shelf","bookshelf","cushion",
                          "blanket","comforter","home","decor","kitchen","kettle","vase","mattress"],
        "fashion":       ["shirt","dress","kurta","jeans","blazer","trouser","kurti","saree",
                          "jacket","t-shirt","fashion","clothing","wear","outfit","style","ethnic"],
        "beauty":        ["serum","moisturiser","moisturizer","facewash","face wash","skincare",
                          "haircare","hair oil","lipstick","makeup","beauty","skincare","shampoo",
                          "conditioner","sunscreen","toner","foundation"],
        "sports-fitness":["running","shoes","yoga","dumbbell","fitness","gym","sport","football",
                          "badminton","cricket","protein","supplement","exercise","workout"],
        "accessories":   ["watch","bag","wallet","handbag","sunglasses","jewellery","jewelry",
                          "necklace","perfume","belt","backpack","purse","accessories"],
        "books-lifestyle":["book","novel","kindle","notebook","journal","pen","planner","diary",
                          "stationery","incense","meditation","wellness","lifestyle","read"],
    }

    detected_cat = None
    best_score = 0
    for cat_slug, keywords in cat_map.items():
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > best_score:
            best_score = score
            detected_cat = cat_slug

    # ── 3. Build DB query ────────────────────────────────────────────
    where_parts = ["p.is_active=1", "p.approval_status='approved'"]
    params = []

    if budget:
        where_parts.append("COALESCE(p.sale_price, p.price) <= ?")
        params.append(budget)

    if detected_cat and best_score > 0:
        where_parts.append("c.slug = ?")
        params.append(detected_cat)
    else:
        # Full-text search fallback
        words = [w for w in re.split(r'\W+', q_lower) if len(w) > 2]
        if words:
            search_conditions = []
            for word in words[:4]:
                search_conditions.append(
                    "(p.name LIKE ? OR p.description LIKE ? OR p.tags LIKE ?)"
                )
                params.extend([f"%{word}%"] * 3)
            where_parts.append(f"({' OR '.join(search_conditions)})")

    where_sql = " AND ".join(where_parts)

    products = rows_to_list(db.execute(
        f"""SELECT p.slug, p.name, p.price, p.sale_price, p.image,
                   p.rating, p.review_count, p.brand,
                   c.name as cat_name
            FROM products p JOIN categories c ON p.category_id=c.id
            WHERE {where_sql}
            ORDER BY p.rating DESC, COALESCE(p.sale_price,p.price) ASC
            LIMIT 6""",
        params
    ).fetchall())

    # ── 4. Generate response text ────────────────────────────────────
    if not products:
        response = (
            f"I couldn't find exact matches for your query. "
            f"Try browsing our full catalogue or refining your search!"
        )
        # Fallback: show featured products
        products = rows_to_list(db.execute(
            """SELECT p.slug, p.name, p.price, p.sale_price, p.image,
                      p.rating, p.review_count, p.brand, c.name as cat_name
               FROM products p JOIN categories c ON p.category_id=c.id
               WHERE p.is_featured=1 AND p.is_active=1
               ORDER BY p.rating DESC LIMIT 4"""
        ).fetchall())
    else:
        parts = []
        if detected_cat and best_score > 0:
            cat_label = detected_cat.replace("-", " ").title()
            parts.append(f"I found {len(products)} great {cat_label} options")
        else:
            parts.append(f"Here are {len(products)} results")

        if budget:
            parts.append(f"within your budget of \u20b9{int(budget):,}")

        response = f"{' '.join(parts)} for you:"
        if len(products) >= 2:
            best = products[0]
            best_price = best["sale_price"] or best["price"]
            response += f" The top recommendation is **{best['name']}** at \u20b9{int(best_price):,}"
            if best["rating"]:
                response += f" with a {best['rating']}/5 rating"
            response += "."

    return jsonify({"response": response, "products": products})


# ── Discover & Deals pages ────────────────────────────────────────────────────
# Dedicated, self-contained pages. They only READ from the database and do not
# touch the existing /shop listing, cart, wishlist or checkout code.

_LIVE_PRODUCT_SQL = (
    "SELECT p.*, c.name AS cat_name, c.slug AS cat_slug "
    "FROM products p JOIN categories c ON p.category_id=c.id "
    "WHERE p.is_active=1 AND p.approval_status='approved' "
)
_DISCOUNT_SQL = "((p.price - p.sale_price) * 100.0 / p.price)"
_REAL_SALE_SQL = "p.sale_price IS NOT NULL AND p.price > 0 AND p.sale_price < p.price"


def _add_discount(products):
    """Attach integer discount % and rupee savings to each product dict."""
    for p in products:
        price, sale = p.get("price"), p.get("sale_price")
        if sale and price and sale < price:
            p["off_pct"] = int(round((price - sale) * 100.0 / price))
            p["saving"] = price - sale
        else:
            p["off_pct"] = 0
            p["saving"] = 0
    return products


@shop_bp.route("/discover")
def discover():
    db = get_db()

    categories = rows_to_list(db.execute(
        """SELECT c.*,
                  (SELECT COUNT(*) FROM products p
                    WHERE p.category_id=c.id AND p.is_active=1
                      AND p.approval_status='approved') AS product_count
           FROM categories c WHERE c.is_active=1 ORDER BY c.sort_order"""
    ).fetchall())

    trending = _add_discount(rows_to_list(db.execute(
        _LIVE_PRODUCT_SQL +
        "ORDER BY (COALESCE(p.rating,0) * COALESCE(p.review_count,0)) DESC, p.id LIMIT 8"
    ).fetchall()))

    fresh = _add_discount(rows_to_list(db.execute(
        _LIVE_PRODUCT_SQL + "ORDER BY p.created_at DESC, p.id DESC LIMIT 8"
    ).fetchall()))

    budget = _add_discount(rows_to_list(db.execute(
        _LIVE_PRODUCT_SQL +
        "AND COALESCE(p.sale_price, p.price) <= 999 "
        "ORDER BY COALESCE(p.rating,0) DESC, p.id LIMIT 8"
    ).fetchall()))

    total_products = db.execute(
        "SELECT COUNT(*) FROM products WHERE is_active=1 AND approval_status='approved'"
    ).fetchone()[0]

    return render_template(
        "shop/discover.html",
        categories=categories,
        trending=trending,
        fresh=fresh,
        budget=budget,
        total_products=total_products,
    )


@shop_bp.route("/deals")
def deals():
    db = get_db()

    cat_slug = request.args.get("category", "").strip()
    min_off = request.args.get("min_off", 0, type=int) or 0
    if min_off not in (0, 10, 20, 30):
        min_off = 0
    sort = request.args.get("sort", "discount")
    sort_map = {
        "discount":   f"{_DISCOUNT_SQL} DESC, p.id",
        "price_asc":  "p.sale_price ASC, p.id",
        "price_desc": "p.sale_price DESC, p.id",
        "rating":     "COALESCE(p.rating,0) DESC, p.id",
    }
    if sort not in sort_map:
        sort = "discount"

    where = " AND " + _REAL_SALE_SQL
    params = []
    if cat_slug:
        where += " AND c.slug=?"
        params.append(cat_slug)
    if min_off:
        where += f" AND {_DISCOUNT_SQL} >= ?"
        params.append(min_off)

    products = _add_discount(rows_to_list(db.execute(
        _LIVE_PRODUCT_SQL + where + f" ORDER BY {sort_map[sort]} LIMIT 60",
        params
    ).fetchall()))

    # Stats + tier counts always describe ALL live deals (not the filtered view)
    stats = db.execute(
        f"""SELECT COUNT(*) AS n,
                   COALESCE(MAX({_DISCOUNT_SQL}), 0) AS best,
                   COALESCE(SUM(p.price - p.sale_price), 0) AS total_saving
            FROM products p JOIN categories c ON p.category_id=c.id
            WHERE p.is_active=1 AND p.approval_status='approved' AND {_REAL_SALE_SQL}"""
    ).fetchone()
    tier_counts = {}
    for tier in (0, 10, 20, 30):
        tier_counts[tier] = db.execute(
            f"""SELECT COUNT(*) FROM products p JOIN categories c ON p.category_id=c.id
                WHERE p.is_active=1 AND p.approval_status='approved' AND {_REAL_SALE_SQL}
                  AND {_DISCOUNT_SQL} >= ?""", (tier,)
        ).fetchone()[0]

    categories = rows_to_list(db.execute(
        "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
    ).fetchall())

    # Biggest saving overall — shown as the highlighted "top deal"
    top_deal = None
    row = db.execute(
        _LIVE_PRODUCT_SQL + " AND " + _REAL_SALE_SQL +
        f" ORDER BY {_DISCOUNT_SQL} DESC, p.id LIMIT 1"
    ).fetchone()
    if row:
        top_deal = _add_discount([dict(row)])[0]

    return render_template(
        "shop/deals.html",
        products=products,
        categories=categories,
        current_cat=cat_slug,
        min_off=min_off,
        sort=sort,
        deal_count=stats["n"],
        best_off=int(round(stats["best"] or 0)),
        tier_counts=tier_counts,
        top_deal=top_deal,
    )
