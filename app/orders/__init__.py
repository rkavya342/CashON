"""app/orders/__init__.py — Orders blueprint."""
from flask import Blueprint

orders_bp = Blueprint("orders", __name__)

from . import routes  # noqa: F401, E402
