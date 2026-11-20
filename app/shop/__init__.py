"""app/shop/__init__.py — Shop blueprint registration."""
from flask import Blueprint

shop_bp = Blueprint("shop", __name__)

from . import routes  # noqa: F401, E402
