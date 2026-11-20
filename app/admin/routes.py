"""app/admin/routes.py — Admin routes (stubs for Phase 1)."""
from flask import render_template
from . import admin_bp


@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")
