"""API Route Blueprints."""
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, abort

api_bp = Blueprint("api", __name__)
POSTS_DB = []


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify the API is responsive."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@api_bp.route("/posts", methods=["GET"])
def get_posts():
    """Retrieve all submitted posts."""
    return jsonify({
        "status": "success",
        "count": len(POSTS_DB),
        "data": POSTS_DB
    }), 200


@api_bp.route("/posts", methods=["POST"])
def create_post():
    """Create a new post entry."""
    payload = request.get_json(silent=True)
    if not payload:
        abort(400, description="Request body must be valid JSON.")

    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    author = (payload.get("author") or "Anonymous").strip()

    if not title or not content:
        abort(400, description="Both 'title' and 'content' are required fields.")

    new_post = {
        "id": len(POSTS_DB) + 1,
        "title": title,
        "content": content,
        "author": author,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    POSTS_DB.append(new_post)

    return jsonify({
        "status": "success",
        "message": "Post created successfully.",
        "data": new_post
    }), 201
