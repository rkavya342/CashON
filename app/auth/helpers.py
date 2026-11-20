"""
app/auth/helpers.py — Auth utility functions and decorators.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(f):
    """
    Route decorator: redirect unauthenticated users to login.
    After login, 'next' param brings them back to the original page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Route decorator: restrict to admin role only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("shop.index"))
        return f(*args, **kwargs)
    return decorated
