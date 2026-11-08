"""API Route Blueprints for submissions, leaderboard, likes, and comments."""
import os
import uuid
from datetime import datetime, timezone
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
)
from werkzeug.utils import secure_filename
from db import get_db

api_bp = Blueprint("api", __name__)


def _allowed_file(filename: str) -> bool:
    """Verify the file has an allowed image extension."""
    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"png", "jpg", "jpeg", "webp", "gif"})
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _save_uploaded_image(file_storage, prefix: str) -> str:
    """Save an uploaded image to UPLOAD_FOLDER and return its public URL path."""
    upload_dir = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_dir, exist_ok=True)

    ext = secure_filename(file_storage.filename).rsplit(".", 1)[1].lower()
    unique_filename = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    file_storage.save(file_path)

    return f"/api/uploads/{unique_filename}"


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify the API is responsive."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@api_bp.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploaded_file(filename: str):
    """Serve uploaded before/after cleanup images."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@api_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    """Return top 5 cleaners ranked by combined submission + completed task points."""
    db = get_db()
    rows = db.execute(
        """
        SELECT name, SUM(points) AS points
        FROM (
            SELECT user_name AS name, points FROM submissions
            UNION ALL
            SELECT assigned_to AS name, pts_worth AS points FROM tasks WHERE status = 2
        )
        GROUP BY LOWER(name)
        ORDER BY points DESC
        LIMIT 5
        """
    ).fetchall()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]}), 200


@api_bp.route("/submissions", methods=["GET"])
@api_bp.route("/posts", methods=["GET"])
def get_submissions():
    """Retrieve all cleanup submissions with their likes and comments, newest first."""
    db = get_db()
    current_user = session.get("user")
    current_sub = current_user.get("sub") if current_user else None

    rows = db.execute(
        """
        SELECT id, user_name, user_email, description, cleaned_on,
               before_image_url, after_image_url, points, created_at
        FROM submissions
        ORDER BY cleaned_on DESC, id DESC
        """
    ).fetchall()

    submissions = []
    for row in rows:
        post = dict(row)
        post_id = post["id"]

        # Count likes and check if current user liked this post
        likes = db.execute(
            "SELECT user_sub FROM post_likes WHERE post_id = ?", (post_id,)
        ).fetchall()
        post["like_count"] = len(likes)
        post["liked_by_me"] = any(r["user_sub"] == current_sub for r in likes) if current_sub else False

        # Fetch comments for this post
        comments = db.execute(
            """
            SELECT id, user_name, body, created_at
            FROM post_comments
            WHERE post_id = ?
            ORDER BY id ASC
            """,
            (post_id,),
        ).fetchall()
        post["comments"] = [dict(c) for c in comments]
        submissions.append(post)

    return jsonify({
        "status": "success",
        "count": len(submissions),
        "data": submissions,
    }), 200


@api_bp.route("/submissions", methods=["POST"])
def create_submission():
    """Handle multipart form upload from submit.html."""
    user = session.get("user")
    if not user:
        return jsonify({
            "error": "Unauthorized",
            "message": "You must be signed in to submit a cleanup."
        }), 401

    before_file = request.files.get("before_image")
    after_file = request.files.get("after_image")

    if not before_file or not before_file.filename or not after_file or not after_file.filename:
        abort(400, description="Both 'before_image' and 'after_image' files are required.")

    if not _allowed_file(before_file.filename) or not _allowed_file(after_file.filename):
        abort(400, description="Only image files (png, jpg, jpeg, webp, gif) are allowed.")

    description = (request.form.get("description") or "").strip()
    cleaned_on = (request.form.get("cleaned_on") or "").strip()

    if not description or not cleaned_on:
        abort(400, description="Both 'description' and 'cleaned_on' are required.")

    before_url = _save_uploaded_image(before_file, "before")
    after_url = _save_uploaded_image(after_file, "after")
    created_at = datetime.now(timezone.utc).isoformat()

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO submissions (
            user_sub, user_name, user_email, description,
            cleaned_on, before_image_url, after_image_url, points, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 10, ?)
        """,
        (
            user.get("sub", "unknown"),
            user.get("name") or user.get("email") or "Anonymous",
            user.get("email"),
            description,
            cleaned_on,
            before_url,
            after_url,
            created_at,
        ),
    )
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            "status": "success",
            "message": "Cleanup submitted successfully!",
            "id": cursor.lastrowid,
            "before_image_url": before_url,
            "after_image_url": after_url,
        }), 201

    return redirect("/posts.html")


@api_bp.route("/posts/<int:post_id>/like", methods=["POST"])
def toggle_like(post_id: int):
    """Toggle a like on a post for the currently signed-in user."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    user_sub = user["sub"]
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM post_likes WHERE post_id = ? AND user_sub = ?",
        (post_id, user_sub),
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM post_likes WHERE post_id = ? AND user_sub = ?",
            (post_id, user_sub),
        )
        liked = False
    else:
        db.execute(
            "INSERT INTO post_likes (post_id, user_sub) VALUES (?, ?)",
            (post_id, user_sub),
        )
        liked = True

    db.commit()

    count = db.execute(
        "SELECT COUNT(*) AS cnt FROM post_likes WHERE post_id = ?", (post_id,)
    ).fetchone()["cnt"]

    return jsonify({"liked": liked, "like_count": count}), 200


@api_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
def add_comment(post_id: int):
    """Add a comment to a post for the currently signed-in user."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or request.form
    body = (payload.get("body") or "").strip()
    if not body:
        abort(400, description="Comment body cannot be empty.")

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_name = user.get("name") or user.get("email") or "Anonymous"

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO post_comments (post_id, user_sub, user_name, body, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (post_id, user["sub"], user_name, body[:300], created_at),
    )
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({
            "id": cursor.lastrowid,
            "user_name": user_name,
            "body": body[:300],
            "created_at": created_at,
        }), 201

    return redirect("/posts.html")

STATUS_MAP = {0: "open", 1: "pending", 2: "done"}


def _is_admin(user: dict | None) -> bool:
    """Return True if the user is an admin (or if no ADMIN_EMAILS restriction is set)."""
    if not user:
        return False
    admin_emails = current_app.config.get("ADMIN_EMAILS", [])
    if not admin_emails:
        return True
    return (user.get("email") or "").lower() in admin_emails


@api_bp.route("/tasks", methods=["GET"])
def get_tasks():
    """
    Return all tasks sorted with open/pending tasks first (by soonest due_on),
    and finished tasks (status = 2) at the bottom.
    """
    db = get_db()
    rows = db.execute(
        """
        SELECT id, task_name, assigned_to, assigned_by, due_on,
               pts_worth, description, photo_url, status, created_at
        FROM tasks
        ORDER BY (status = 2) ASC, due_on ASC, id ASC
        """
    ).fetchall()

    tasks = []
    for row in rows:
        t = dict(row)
        t["status_label"] = STATUS_MAP.get(t["status"], "open")
        tasks.append(t)

    return jsonify({"status": "success", "count": len(tasks), "data": tasks}), 200


@api_bp.route("/tasks", methods=["POST"])
def create_task():
    """Create a new cleaning task (Admin only)."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only admins can assign tasks."}), 403

    # Support both multipart form-data (from tasks.html) and JSON
    task_name = (request.form.get("place") or "").strip()
    assigned_to = (request.form.get("assignee") or "").strip()
    due_on = (request.form.get("due_on") or "").strip()
    description = (request.form.get("description") or "").strip()
    pts_raw = request.form.get("points", "10")

    try:
        pts_worth = int(pts_raw)
        if not (1 <= pts_worth <= 100):
            raise ValueError
    except ValueError:
        abort(400, description="'points' must be a whole number between 1 and 100.")

    if not task_name or not assigned_to or not due_on or not description:
        abort(400, description="'place', 'assignee', 'due_on', and 'description' are required.")

    photo_url = None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        if not _allowed_file(photo_file.filename):
            abort(400, description="Invalid image format for task photo.")
        photo_url = _save_uploaded_image(photo_file, "task")

    assigned_by = user.get("name") or user.get("email") or "Admin"
    created_at = datetime.now(timezone.utc).isoformat()

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO tasks (
            task_name, assigned_to, assigned_by, due_on,
            pts_worth, description, photo_url, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (task_name, assigned_to, assigned_by, due_on, pts_worth, description, photo_url, created_at),
    )
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "id": cursor.lastrowid}), 201

    return redirect("/tasks.html")


@api_bp.route("/tasks/<int:task_id>/done", methods=["POST"])
def mark_task_done(task_id: int):
    """Transition a task from open (0) to pending approval (1)."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        abort(404)

    # Check that the signed-in user matches the assignee (case-insensitive) or is an admin
    user_name = (user.get("name") or "").strip().lower()
    user_email = (user.get("email") or "").strip().lower()
    assignee = task["assigned_to"].strip().lower()

    if assignee not in (user_name, user_email) and not user_name.startswith(assignee) and not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only the assigned member can mark this task done."}), 403

    db.execute("UPDATE tasks SET status = 1 WHERE id = ?", (task_id,))
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "new_status": 1}), 200
    return redirect("/tasks.html")


@api_bp.route("/tasks/<int:task_id>/approve", methods=["POST"])
def approve_task(task_id: int):
    """Transition a task from pending (1) to done (2) (Admin only)."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only admins can approve tasks."}), 403

    db = get_db()
    db.execute("UPDATE tasks SET status = 2 WHERE id = ?", (task_id,))
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "new_status": 2}), 200
    return redirect("/tasks.html")


@api_bp.route("/tasks/<int:task_id>/reopen", methods=["POST"])
def reopen_task(task_id: int):
    """Send a pending task (1) back to open (0) (Admin only)."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only admins can reopen tasks."}), 403

    db = get_db()
    db.execute("UPDATE tasks SET status = 0 WHERE id = ?", (task_id,))
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "new_status": 0}), 200
    return redirect("/tasks.html")