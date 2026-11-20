"""
app/orders/routes.py — CASHON Orders, Checkout & Payments v2
Simulated payment flow: success, failure, pending statuses.
Full checkout, order confirmation, order history, and refunds.
Currency: INR (Indian Rupees)
"""

import json
import random
import string
from datetime import datetime
from flask import (
    render_template, redirect, url_for, request,
    session, flash, jsonify
)
from app.db import get_db
from . import orders_bp


def login_required_redirect(next_url=None):
    return redirect(url_for("auth.login", next=next_url or request.path))


def gen_order_number():
    return "CASH" + datetime.now().strftime("%Y%m%d") + "".join(
        random.choices(string.digits, k=4)
    )


def gen_payment_ref():
    return "PAY" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


# ── Checkout ─────────────────────────────────────────────────────────────────

@orders_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return login_required_redirect("/orders/checkout")

    db = get_db()
    cart_items = db.execute(
        """SELECT ci.*, p.name, p.slug, p.image, p.stock,
                  COALESCE(p.sale_price, p.price) as unit_price,
                  p.price as original_price
           FROM cart_items ci
           JOIN products p ON ci.product_id=p.id
           WHERE ci.user_id=?""",
        (session["user_id"],)
    ).fetchall()

    if not cart_items:
        flash("Your cart is empty.", "info")
        return redirect(url_for("shop.cart"))

    cart_items = [dict(r) for r in cart_items]
    subtotal = sum(item["unit_price"] * item["qty"] for item in cart_items)

    addresses = db.execute(
        "SELECT * FROM addresses WHERE user_id=? ORDER BY is_default DESC",
        (session["user_id"],)
    ).fetchall()
    addresses = [dict(a) for a in addresses]

    # Apply coupon
    coupon_code  = request.args.get("coupon", "").upper().strip()
    coupon_data  = None
    coupon_discount = 0

    if coupon_code:
        coupon_row = db.execute(
            """SELECT * FROM coupons
               WHERE code=? AND is_active=1
               AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
               AND (uses_left < 0 OR uses_left > 0)""",
            (coupon_code,)
        ).fetchone()
        if coupon_row:
            coupon_data = dict(coupon_row)
            if subtotal >= coupon_data["min_order"]:
                if coupon_data["type"] == "fixed":
                    coupon_discount = min(coupon_data["value"], coupon_data["max_discount"] or coupon_data["value"])
                elif coupon_data["type"] == "percent":
                    pct = coupon_data["value"] / 100
                    coupon_discount = min(subtotal * pct, coupon_data["max_discount"] or 999999)
                coupon_discount = round(coupon_discount)

    shipping_fee = 0 if subtotal >= 499 else 99
    tax_rate = 0.18  # 18% GST
    taxable = max(0, subtotal - coupon_discount)
    tax = round(taxable * tax_rate / (1 + tax_rate))  # tax-inclusive (reverse)
    total = taxable + shipping_fee

    if request.method == "GET":
        return render_template(
            "orders/checkout.html",
            cart_items=cart_items,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            coupon_discount=coupon_discount,
            coupon_code=coupon_code,
            coupon_data=coupon_data,
            tax=tax,
            total=total,
            addresses=addresses,
        )

    # POST — place order ──────────────────────────────────────────────
    address_id    = request.form.get("address_id", type=int)
    payment_method = request.form.get("payment_method", "card")
    new_name  = request.form.get("new_name", "").strip()
    new_phone = request.form.get("new_phone", "").strip()
    new_line1 = request.form.get("new_line1", "").strip()
    new_city  = request.form.get("new_city",  "").strip()
    new_state = request.form.get("new_state", "").strip()
    new_pin   = request.form.get("new_pin",   "").strip()

    # Create address if new address submitted
    if new_line1 and new_city and not address_id:
        cur = db.execute(
            """INSERT INTO addresses (user_id,label,full_name,phone,line1,city,state,pincode,country,is_default)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (session["user_id"], "Home", new_name or session["name"],
             new_phone, new_line1, new_city, new_state, new_pin, "India", 0)
        )
        address_id = cur.lastrowid

    if not address_id:
        flash("Please select or add a delivery address.", "danger")
        return redirect(url_for("orders.checkout"))

    addr = db.execute("SELECT * FROM addresses WHERE id=? AND user_id=?",
                      (address_id, session["user_id"])).fetchone()
    if not addr:
        flash("Invalid address.", "danger")
        return redirect(url_for("orders.checkout"))

    addr_snap = json.dumps(dict(addr))
    order_num = gen_order_number()

    # Simulated payment result
    payment_result = _simulate_payment(payment_method)

    # Create order
    cur = db.execute(
        """INSERT INTO orders
           (user_id,order_number,total,subtotal,discount,shipping_fee,
            status,payment_status,payment_method,payment_ref,
            address_id,address_snapshot,coupon_code)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session["user_id"], order_num, total, subtotal,
         coupon_discount, shipping_fee,
         "confirmed" if payment_result["success"] else "pending",
         payment_result["payment_status"],
         payment_method, payment_result["ref"],
         address_id, addr_snap, coupon_code or None)
    )
    order_id = cur.lastrowid

    # Order items
    for item in cart_items:
        db.execute(
            """INSERT INTO order_items (order_id,product_id,name,image,qty,unit_price,size,colour)
               VALUES (?,?,?,?,?,?,?,?)""",
            (order_id, item["product_id"], item["name"], item["image"],
             item["qty"], item["unit_price"],
             item.get("size", ""), item.get("colour", ""))
        )
        # Reduce stock
        db.execute(
            "UPDATE products SET stock=MAX(0,stock-?) WHERE id=?",
            (item["qty"], item["product_id"])
        )

    # Deduct coupon use
    if coupon_code and coupon_data:
        db.execute(
            "UPDATE coupons SET uses_left=CASE WHEN uses_left>0 THEN uses_left-1 ELSE uses_left END WHERE code=?",
            (coupon_code,)
        )

    # Clear cart
    db.execute("DELETE FROM cart_items WHERE user_id=?", (session["user_id"],))

    # Notification
    db.execute(
        """INSERT INTO notifications (user_id,type,title,message,link)
           VALUES (?,?,?,?,?)""",
        (session["user_id"], "order",
         f"Order #{order_num} placed!",
         f"Your order has been placed. Payment status: {payment_result['payment_status']}.",
         f"/orders/{order_id}")
    )

    db.commit()

    return redirect(url_for("orders.confirmation", order_id=order_id))


def _simulate_payment(method):
    """Simulate payment with realistic success/failure rates."""
    # UPI: 95% success, Card: 92%, Wallet: 88%, COD: always success
    success_rates = {"upi": 0.95, "card": 0.92, "wallet": 0.88, "cod": 1.0, "netbanking": 0.90}
    rate = success_rates.get(method, 0.9)
    success = random.random() < rate

    if method == "cod":
        return {"success": True, "payment_status": "pending", "ref": "COD"}

    if success:
        return {"success": True, "payment_status": "paid", "ref": gen_payment_ref()}
    else:
        # Simulate a declined payment (5-10% failure) — still create order as 'pending'
        return {"success": False, "payment_status": "failed", "ref": gen_payment_ref()}


# ── Order Confirmation ────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/confirmation")
def confirmation(order_id):
    if "user_id" not in session:
        return login_required_redirect()

    db  = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, session["user_id"])
    ).fetchone()

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("auth.order_history"))

    items = db.execute(
        "SELECT * FROM order_items WHERE order_id=?", (order_id,)
    ).fetchall()

    addr = json.loads(order["address_snapshot"]) if order["address_snapshot"] else {}

    return render_template(
        "orders/confirmation.html",
        order=dict(order),
        items=[dict(i) for i in items],
        addr=addr,
    )


# ── Order History ─────────────────────────────────────────────────────────────

@orders_bp.route("/")
def order_list():
    if "user_id" not in session:
        return login_required_redirect("/orders/")

    db = get_db()
    orders = db.execute(
        """SELECT o.*, COUNT(oi.id) as item_count
           FROM orders o
           LEFT JOIN order_items oi ON oi.order_id=o.id
           WHERE o.user_id=?
           GROUP BY o.id
           ORDER BY o.created_at DESC""",
        (session["user_id"],)
    ).fetchall()

    return render_template("orders/list.html", orders=[dict(o) for o in orders])


# ── Order Detail ──────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>")
def order_detail(order_id):
    if "user_id" not in session:
        return login_required_redirect()

    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, session["user_id"])
    ).fetchone()

    if not order:
        flash("Order not found.", "danger")
        return redirect(url_for("orders.order_list"))

    items  = [dict(i) for i in db.execute(
        "SELECT * FROM order_items WHERE order_id=?", (order_id,)
    ).fetchall()]

    addr   = json.loads(order["address_snapshot"]) if order["address_snapshot"] else {}
    coupon = None
    if order["coupon_code"]:
        coupon = db.execute(
            "SELECT * FROM coupons WHERE code=?", (order["coupon_code"],)
        ).fetchone()

    return render_template(
        "orders/detail.html",
        order=dict(order),
        items=items,
        addr=addr,
        coupon=dict(coupon) if coupon else None,
    )


# ── Cancel Order ──────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, session["user_id"])
    ).fetchone()

    if not order:
        return jsonify({"ok": False, "message": "Order not found."}), 404

    if order["status"] not in ("placed", "confirmed"):
        return jsonify({"ok": False, "message": "This order cannot be cancelled."}), 400

    db.execute(
        "UPDATE orders SET status='cancelled', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (order_id,)
    )

    # Restore stock
    items = db.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    for item in items:
        db.execute(
            "UPDATE products SET stock=stock+? WHERE id=?",
            (item["qty"], item["product_id"])
        )

    # Create refund record if payment was paid
    if order["payment_status"] == "paid":
        db.execute(
            """INSERT INTO refunds (order_id,user_id,amount,reason,status)
               VALUES (?,?,?,?,?)""",
            (order_id, session["user_id"], order["total"], "Customer cancelled", "processing")
        )
        db.execute(
            """INSERT INTO notifications (user_id,type,title,message,link)
               VALUES (?,?,?,?,?)""",
            (session["user_id"], "refund",
             "Refund initiated",
             f"Refund of \u20b9{order['total']:,} for order #{order['order_number']} is being processed.",
             f"/orders/{order_id}")
        )

    db.execute(
        """INSERT INTO notifications (user_id,type,title,message,link)
           VALUES (?,?,?,?,?)""",
        (session["user_id"], "order",
         f"Order #{order['order_number']} cancelled",
         "Your order has been successfully cancelled.",
         f"/orders/{order_id}")
    )

    db.commit()
    flash("Your order has been cancelled.", "success")
    return jsonify({"ok": True})


# ── Retry Payment ─────────────────────────────────────────────────────────────

@orders_bp.route("/<int:order_id>/retry-payment", methods=["POST"])
def retry_payment(order_id):
    if "user_id" not in session:
        return jsonify({"ok": False}), 401

    db = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=? AND payment_status='failed'",
        (order_id, session["user_id"])
    ).fetchone()

    if not order:
        return jsonify({"ok": False, "message": "Order not eligible for payment retry."}), 400

    result = _simulate_payment(order["payment_method"])

    if result["success"]:
        db.execute(
            """UPDATE orders SET payment_status='paid', payment_ref=?,
               status='confirmed', updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (result["ref"], order_id)
        )
        db.execute(
            """INSERT INTO notifications (user_id,type,title,message,link)
               VALUES (?,?,?,?,?)""",
            (session["user_id"], "payment",
             "Payment successful!",
             f"Payment for order #{order['order_number']} was successful.",
             f"/orders/{order_id}")
        )
        db.commit()
        return jsonify({"ok": True, "message": "Payment successful!"})
    else:
        return jsonify({"ok": False, "message": "Payment declined again. Please try a different method."})


# ── Apply Coupon API ──────────────────────────────────────────────────────────

@orders_bp.route("/api/apply-coupon", methods=["POST"])
def api_apply_coupon():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip().upper()
    subtotal = float(data.get("subtotal", 0))

    if not code:
        return jsonify({"ok": False, "message": "Please enter a coupon code."})

    db = get_db()
    coupon = db.execute(
        """SELECT * FROM coupons
           WHERE code=? AND is_active=1
           AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
           AND (uses_left < 0 OR uses_left > 0)""",
        (code,)
    ).fetchone()

    if not coupon:
        return jsonify({"ok": False, "message": "Invalid or expired coupon code."})

    coupon = dict(coupon)

    if subtotal < coupon["min_order"]:
        return jsonify({
            "ok": False,
            "message": f"This coupon requires a minimum order of \u20b9{int(coupon['min_order']):,}."
        })

    if coupon["type"] == "fixed":
        discount = min(coupon["value"], coupon.get("max_discount") or coupon["value"])
    elif coupon["type"] == "percent":
        discount = min(subtotal * coupon["value"] / 100, coupon.get("max_discount") or 999999)
    else:
        discount = 0

    discount = round(discount)
    return jsonify({
        "ok": True,
        "discount": discount,
        "message": f"Coupon applied! You save \u20b9{discount:,}.",
        "description": coupon["description"],
    })
