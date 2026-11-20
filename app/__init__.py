"""
app/__init__.py — Flask application factory.

Using the app-factory pattern lets you create multiple instances
(testing, development, production) without circular imports.
"""

import os
import secrets
from flask import Flask, g, session, request
from datetime import timedelta

from .db import init_db, get_db


def create_app(test_config=None):
    """Create and configure the Flask application."""

    app = Flask(__name__, instance_relative_config=True)

    # ── Core configuration ───────────────────────────────────────────────
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", secrets.token_hex(32)),
        DATABASE=os.path.join(app.instance_path, "cashon.db"),
        UPLOAD_FOLDER=os.path.join(os.path.dirname(app.root_path), "uploads"),
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,          # 10 MB max upload
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # stay logged in for a week
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    # Ensure folders exist
    for folder in [app.instance_path, app.config["UPLOAD_FOLDER"]]:
        os.makedirs(folder, exist_ok=True)

    # ── CLI command to initialise the database ──────────────────────────
    @app.cli.command("init-db")
    def init_db_command():
        """Drop and recreate all tables from schema.sql."""
        init_db(app)
        print("✅  Database initialised.")

    # ── Close DB connection after every request ──────────────────────────
    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    # ── Keep sessions alive on each request ─────────────────────────────
    @app.before_request
    def refresh_session():
        if "user_id" in session:
            session.permanent = True

    # ── Register Blueprints ──────────────────────────────────────────────
    from .auth   import auth_bp
    from .shop   import shop_bp
    from .orders import orders_bp
    from .admin  import admin_bp

    app.register_blueprint(auth_bp,   url_prefix="/account")
    app.register_blueprint(shop_bp)                             # / and /shop/*
    app.register_blueprint(orders_bp, url_prefix="/orders")
    app.register_blueprint(admin_bp,  url_prefix="/admin")

    # Seller blueprint (optional — stub if module not yet fully implemented)
    try:
        from .seller import seller_bp
        app.register_blueprint(seller_bp, url_prefix="/seller")
    except (ImportError, AttributeError):
        # Register a minimal seller stub so url_for('seller.dashboard') works
        from flask import Blueprint, redirect, url_for as _url_for
        _seller = Blueprint("seller", __name__)

        @_seller.route("/")
        def dashboard():
            return redirect(_url_for("shop.index"))

        app.register_blueprint(_seller, url_prefix="/seller")

    # ── Inject globals into every template ──────────────────────────────
    @app.context_processor
    def inject_globals():
        """Make cart count and current user available in every template."""
        cart_count = 0
        if "user_id" in session:
            try:
                db = get_db()
                row = db.execute(
                    "SELECT COALESCE(SUM(qty),0) FROM cart_items WHERE user_id=?",
                    (session["user_id"],)
                ).fetchone()
                cart_count = row[0] if row else 0
            except Exception:
                pass
        return {"cart_count": cart_count}

    # ── Custom error pages ───────────────────────────────────────────────
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    return app
