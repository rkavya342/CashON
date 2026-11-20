"""
run.py — Application entry point.

Usage:
    python run.py

The app will start on http://localhost:5000
Set DEBUG=0 in environment to disable debug mode for production.
"""

import os
try:
    from app import create_app
except ModuleNotFoundError as exc:
    if exc.name:
        print(
            f"Missing Python dependency: {exc.name}.\\n"
            "From this folder run: python -m pip install -r requirements.txt"
        )
    raise

app = create_app()

if __name__ == "__main__":
    # debug=True enables auto-reload and detailed error pages during development
    debug = os.environ.get("DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
