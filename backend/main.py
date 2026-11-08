"""Main entry point for starting the Flask backend server."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    host = app.config.get("HOST", "0.0.0.0")
    port = app.config.get("PORT", 5000)
    debug = app.config.get("DEBUG", True)

    print(f"Starting server on http://{host}:{port} (Debug: {debug})")
    app.run(host=host, port=port, debug=debug)
