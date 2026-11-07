"""JSON API blueprint.

Every endpoint returns JSON so the frontend can consume it with ``fetch``.
Add your own routes here, or create additional blueprints next to this one.
"""

from flask import Blueprint, jsonify, request

api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    """Simple liveness probe used by the frontend to show connection status."""
    return jsonify(status="ok", service="hackcamp-backend")


@api_bp.get("/greeting")
def greeting():
    """GET /api/greeting?name=Ada -> {"message": "Hello, Ada!"}"""
    name = (request.args.get("name") or "").strip() or "World"
    return jsonify(message=f"Hello, {name}!")


@api_bp.post("/echo")
def echo():
    """POST /api/echo with a JSON body -> echoes it back.

    Demonstrates reading JSON request bodies from the frontend.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify(error="Request body must be valid JSON"), 400

    return jsonify(received=payload)
