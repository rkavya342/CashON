"""
app/auth/routes.py — Full authentication routes.

Implements: login (with bcrypt), register, logout, profile view/edit,
wishlist, order history. All with proper session management.
"""

import os
import bcrypt
from flask import (
    render_template, redirect, url_for, request,
    session, flash, current_app
)
from app.db import get_db
from . import auth_bp
from .helpers import login_required


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hash(plain: str) -> str:
    """Hash a password with bcrypt (slow + salted = secure)."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _check(plain: str, hashed: str) -> bool:
    """Compare a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Registration page.
    GET  → show the form.
    POST → validate, create account, auto-login, redirect to homepage.
    """
    # Already logged in? Go home.
    if "user_id" in session:
        return redirect(url_for("shop.index"))

    errors = {}

    if request.method == "POST":
        name     = request.form.get("name",     "").strip()
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm",  "")

        # --- Validation ---
        if not name:
            errors["name"] = "Please enter your name."
        if not email or "@" not in email:
            errors["email"] = "Please enter a valid email address."
        if len(password) < 6:
            errors["password"] = "Password must be at least 6 characters."
        elif password != confirm:
            errors["confirm"] = "Passwords do not match."

        db = get_db()

        if not errors:
            # Check if email already taken
            existing = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if existing:
                errors["email"] = "An account with that email already exists."

        if not errors:
            # Create the account
            db.execute(
                "INSERT INTO users (email, name, password_hash, role) VALUES (?,?,?,?)",
                (email, name, _hash(password), "customer")
            )
            db.commit()

            # Fetch the new user and auto-login
            user = db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

            session.clear()
            session["user_id"] = user["id"]
            session["name"]    = user["name"]
            session["email"]   = user["email"]
            session["role"]    = user["role"]
            session.permanent  = True

            flash(f"Welcome to CashOn, {name}! Your account is ready. 🎉", "success")
            return redirect(url_for("shop.index"))

    return render_template(
        "auth/register.html",
        errors=errors,
        form_data=request.form,
    )


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Login page.
    GET  → show the form.
    POST → validate credentials, set session, redirect.
    """
    if "user_id" in session:
        return redirect(url_for("shop.index"))

    error = None

    if request.method == "POST":
        email    = request.form.get("email",    "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Please fill in both fields."
        else:
            db   = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()

            if not user:
                # Generic message — don't reveal whether email exists
                error = "Invalid email or password. Please try again."
            elif not user["is_active"]:
                error = "Your account has been disabled. Please contact support."
            elif not _check(password, user["password_hash"]):
                error = "Invalid email or password. Please try again."
            else:
                # ✅ Success — set up session
                session.clear()
                session["user_id"] = user["id"]
                session["name"]    = user["name"]
                session["email"]   = user["email"]
                session["role"]    = user["role"]
                session.permanent  = True

                flash(f"Welcome back, {user['name']}! Great to see you. 👋", "success")

                # Redirect to 'next' if it's a safe internal URL
                next_url = request.args.get("next", "")
                if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)
                return redirect(url_for("shop.index"))

    return render_template("auth/login.html", error=error, form_data=request.form)


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route("/logout")
def logout():
    """Clear session and redirect home."""
    name = session.get("name", "")
    session.clear()
    flash(f"See you soon{', ' + name if name else ''}! 👋", "info")
    return redirect(url_for("shop.index"))


# ── Profile ───────────────────────────────────────────────────────────────────

@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and edit the current user's profile."""
    db   = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if request.method == "POST":
        name    = request.form.get("name",  "").strip()
        phone   = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            flash("Name cannot be empty.", "danger")
        else:
            db.execute(
                "UPDATE users SET name=?, phone=?, address=? WHERE id=?",
                (name, phone, address, session["user_id"])
            )
            db.commit()
            session["name"] = name   # keep session in sync
            flash("Profile updated! ✅", "success")
            return redirect(url_for("auth.profile"))

    # Fetch user's orders for the sidebar
    orders = db.execute(
        """SELECT o.*, COUNT(oi.id) as item_count
           FROM orders o
           LEFT JOIN order_items oi ON oi.order_id = o.id
           WHERE o.user_id = ?
           GROUP BY o.id
           ORDER BY o.created_at DESC LIMIT 5""",
        (session["user_id"],)
    ).fetchall()

    # Fetch wishlist count
    wl_count = db.execute(
        "SELECT COUNT(*) as cnt FROM wishlist WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()["cnt"]

    return render_template(
        "auth/profile.html",
        user=user,
        orders=orders,
        wl_count=wl_count,
    )


# ── Change password ───────────────────────────────────────────────────────────

@auth_bp.route("/profile/password", methods=["POST"])
@login_required
def change_password():
    """Handle password change from the profile page."""
    current  = request.form.get("current_password", "")
    new_pw   = request.form.get("new_password", "")
    confirm  = request.form.get("confirm_password", "")

    db   = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id=?", (session["user_id"],)
    ).fetchone()

    if not _check(current, user["password_hash"]):
        flash("Current password is incorrect.", "danger")
    elif len(new_pw) < 6:
        flash("New password must be at least 6 characters.", "danger")
    elif new_pw != confirm:
        flash("New passwords do not match.", "danger")
    else:
        db.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (_hash(new_pw), session["user_id"])
        )
        db.commit()
        flash("Password updated successfully! ✅", "success")

    return redirect(url_for("auth.profile"))


# ── Wishlist page ─────────────────────────────────────────────────────────────

@auth_bp.route("/wishlist")
@login_required
def wishlist():
    """Show all wishlisted products for the logged-in user."""
    db = get_db()
    items = db.execute(
        """SELECT p.*, c.name as cat_name, c.slug as cat_slug
           FROM wishlist w
           JOIN products p ON w.product_id = p.id
           JOIN categories c ON p.category_id = c.id
           WHERE w.user_id = ?
           ORDER BY w.id DESC""",
        (session["user_id"],)
    ).fetchall()
    return render_template("auth/wishlist.html", items=[dict(r) for r in items])


# ── Order history ─────────────────────────────────────────────────────────────

@auth_bp.route("/orders")
@login_required
def order_history():
    """List all orders placed by the logged-in user."""
    db = get_db()
    orders = db.execute(
        """SELECT o.*, COUNT(oi.id) as item_count
           FROM orders o
           LEFT JOIN order_items oi ON oi.order_id = o.id
           WHERE o.user_id = ?
           GROUP BY o.id
           ORDER BY o.created_at DESC""",
        (session["user_id"],)
    ).fetchall()
    import json as _json
    result = []
    for r in orders:
        o = dict(r)
        o["items"] = [dict(i) for i in db.execute(
            """SELECT oi.name, oi.qty, oi.unit_price, oi.size, oi.colour,
                      COALESCE(NULLIF(p.image, ''), oi.image) AS image
               FROM order_items oi LEFT JOIN products p ON p.id = oi.product_id
               WHERE oi.order_id = ?""", (o["id"],)).fetchall()]
        try:
            o["address"] = _json.loads(o["address_snapshot"]) if o.get("address_snapshot") else None
        except ValueError:
            o["address"] = None
        result.append(o)
    return render_template("auth/orders.html", orders=result)


# ── Notifications ─────────────────────────────────────────────────────────────

@auth_bp.route("/notifications")
@login_required
def notifications():
    """Show all notifications for the logged-in user."""
    db = get_db()
    # Mark all as read on view
    db.execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=?",
        (session["user_id"],)
    )
    db.commit()
    items = db.execute(
        """SELECT * FROM notifications WHERE user_id=?
           ORDER BY created_at DESC LIMIT 50""",
        (session["user_id"],)
    ).fetchall()
    return render_template("auth/notifications.html", notifications=[dict(n) for n in items])


@auth_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    db = get_db()
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
    db.commit()
    from flask import jsonify
    return jsonify({"ok": True})
