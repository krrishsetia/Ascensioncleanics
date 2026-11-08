import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import config_by_name
from routes import api_bp, auth_bp


def create_app(env_name: str = None) -> Flask:
    """Application factory function to initialize and configure the Flask app."""
    if not env_name:
        env_name = os.getenv("FLASK_ENV", "default")

    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(config_by_name.get(env_name, config_by_name["default"]))

    # supports_credentials=True is required for session cookies to persist across requests
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # Register API and Authentication blueprints
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    @app.route("/")
    def serve_index():
        """Serve the main frontend entry page."""
        if os.path.exists(os.path.join(frontend_dir, "homepage.html")):
            return send_from_directory(frontend_dir, "homepage.html")
        return jsonify({"status": "running", "message": "Backend API is active."}), 200

    register_error_handlers(app)
    return app


def register_error_handlers(app: Flask) -> None:
    """Attach global HTTP error handlers returning uniform JSON responses."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": str(error.description)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": "The requested resource does not exist."}), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500