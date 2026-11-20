"""app/auth/__init__.py — Auth blueprint registration."""
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

from . import routes  # noqa: F401, E402 — import routes to register them
