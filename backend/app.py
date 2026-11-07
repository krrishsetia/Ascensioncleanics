"""Flask application factory and entrypoint.

The JSON API lives under ``/api``. The static HTML5/JS frontend is served
from the same origin by Flask, so the app runs with a single command.

CORS is enabled so you can also run the frontend from a separate dev
server (e.g. VS Code Live Server) during development.
"""

import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=FRONTEND_DIR,
        static_url_path="",  # serve /css/*, /js/* directly from frontend/
    )
    app.json.sort_keys = False

    # Allow cross-origin requests while developing the frontend separately.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    try:
        # Imported as a package: flask --app backend.app run / WSGI servers.
        from .routes.api import api_bp
    except ImportError:
        # Run directly: python backend/app.py
        from routes.api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    @app.get("/")
    def index():
        """Serve the single-page frontend."""
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/favicon.ico")
    def favicon():
        """Avoid noisy 404s in the browser console."""
        return "", 204

    @app.errorhandler(404)
    def not_found(error):
        """Return JSON for unknown API routes, HTML otherwise."""
        if request.path.startswith("/api/"):
            return jsonify(error="Not found"), 404
        return "<h1>404 Not Found</h1>", 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
