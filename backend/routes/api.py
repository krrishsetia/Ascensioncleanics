"""API Route Blueprints for submissions, leaderboard, tasks, and admin management."""
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
from db import get_db, upsert_user

api_bp = Blueprint("api", __name__)

STATUS_MAP = {0: "open", 1: "pending", 2: "done"}


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


def _is_admin(user: dict | None) -> bool:
    """Return True if the signed-in user is in ADMIN_EMAILS (or if ADMIN_EMAILS is unset in dev)."""
    if not user:
        return False
    admin_emails = current_app.config.get("ADMIN_EMAILS", [])
    if not admin_emails:
        return True
    return (user.get("email") or "").lower() in admin_emails


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint to verify the API is responsive."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@api_bp.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploaded_file(filename: str):
    """Serve uploaded before/after cleanup and task images."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@api_bp.route("/leaderboard", methods=["GET"])
def get_leaderboard():
    """Return top 5 cleaners from the users table ranked by total points."""
    db = get_db()
    rows = db.execute(
        """
        SELECT name, points
        FROM users
        WHERE points > 0
        ORDER BY points DESC, id ASC
        LIMIT 5
        """
    ).fetchall()
    return jsonify({"status": "success", "data": [dict(r) for r in rows]}), 200


@api_bp.route("/submissions", methods=["GET"])
@api_bp.route("/posts", methods=["GET"])
def get_submissions():
    """Retrieve all APPROVED cleanup submissions with their likes and comments, newest first."""
    db = get_db()
    current_user = session.get("user")
    current_sub = current_user.get("sub") if current_user else None

    rows = db.execute(
        """
        SELECT id, user_sub, user_name, user_email, description, cleaned_on,
               before_image_url, after_image_url, points, status, created_at
        FROM submissions
        WHERE status = 'approved'
        ORDER BY cleaned_on DESC, id DESC
        """
    ).fetchall()

    submissions = []
    for row in rows:
        post = dict(row)
        post_id = post["id"]

        likes = db.execute(
            "SELECT user_sub FROM post_likes WHERE post_id = ?", (post_id,)
        ).fetchall()
        post["like_count"] = len(likes)
        post["liked_by_me"] = any(r["user_sub"] == current_sub for r in likes) if current_sub else False

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
    """Handle multipart form upload from submit.html (starts as 'pending')."""
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

    # Ensure user exists in the users table
    db_user = upsert_user(
        sub=user.get("sub", "unknown"),
        name=user.get("name") or user.get("email") or "Anonymous",
        email=user.get("email") or "",
    )

    before_url = _save_uploaded_image(before_file, "before")
    after_url = _save_uploaded_image(after_file, "after")
    created_at = datetime.now(timezone.utc).isoformat()

    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO submissions (
            user_sub, user_name, user_email, description,
            cleaned_on, before_image_url, after_image_url, points, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 10, 'pending', ?)
        """,
        (
            db_user["sub"],
            db_user["name"],
            db_user["email"],
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
            "message": "Cleanup submitted and waiting for admin approval!",
            "id": cursor.lastrowid,
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


# ======================== TASKS ROUTES ========================

@api_bp.route("/tasks", methods=["GET"])
def get_tasks():
    """Return all tasks sorted by soonest due_on first, done tasks last."""
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
    """Approve a pending task (status -> 2) and add its points to the assignee's user total."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only admins can approve tasks."}), 403

    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        abort(404)

    if task["status"] != 2:
        db.execute("UPDATE tasks SET status = 2 WHERE id = ?", (task_id,))
        # Credit points to matching user in users table (if found by name or email)
        assignee = task["assigned_to"].strip()
        db.execute(
            """
            UPDATE users
            SET points = points + ?
            WHERE LOWER(name) = LOWER(?) OR LOWER(email) = LOWER(?)
            """,
            (task["pts_worth"], assignee, assignee),
        )
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


@api_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id: int):
    """Permanently delete a task (Admin only). Points already awarded stay on the user's total."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Only admins can delete tasks."}), 403

    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success"}), 200
    return redirect("/admin.html#manage-tasks")


# ======================== ADMIN ROUTES ========================

@api_bp.route("/admin/overview", methods=["GET"])
def admin_overview():
    """Return pending submissions (oldest first), all tasks, and all users for admin.html."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Admin access required."}), 403

    db = get_db()

    pending_rows = db.execute(
        """
        SELECT id, user_sub, user_name, user_email, description, cleaned_on,
               before_image_url, after_image_url, points, status, created_at
        FROM submissions
        WHERE status = 'pending'
        ORDER BY cleaned_on ASC, id ASC
        """
    ).fetchall()

    task_rows = db.execute(
        """
        SELECT id, task_name, assigned_to, assigned_by, due_on,
               pts_worth, description, photo_url, status, created_at
        FROM tasks
        ORDER BY (status = 2) ASC, due_on ASC, id ASC
        """
    ).fetchall()

    people_rows = db.execute(
        """
        SELECT id, sub, name, email, points
        FROM users
        ORDER BY points DESC, name ASC
        """
    ).fetchall()

    return jsonify({
        "status": "success",
        "pending_submissions": [dict(r) for r in pending_rows],
        "tasks": [dict(r) for r in task_rows],
        "people": [dict(r) for r in people_rows],
    }), 200


@api_bp.route("/admin/submissions/<int:sub_id>/approve", methods=["POST"])
def admin_approve_submission(sub_id: int):
    """Approve a pending submission and add points (0-100) to that person's total."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Admin access required."}), 403

    payload = request.get_json(silent=True) or request.form
    pts_raw = payload.get("points", 10)
    try:
        points = int(pts_raw)
        if not (0 <= points <= 100):
            raise ValueError
    except ValueError:
        abort(400, description="'points' must be a whole number between 0 and 100.")

    db = get_db()
    sub = db.execute("SELECT * FROM submissions WHERE id = ?", (sub_id,)).fetchone()
    if not sub:
        abort(404)

    if sub["status"] != "approved":
        db.execute(
            "UPDATE submissions SET status = 'approved', points = ? WHERE id = ?",
            (points, sub_id),
        )
        # Ensure the submitter is in users table and add points to their total
        upsert_user(sub["user_sub"], sub["user_name"], sub["user_email"] or "")
        db.execute(
            "UPDATE users SET points = points + ? WHERE sub = ?",
            (points, sub["user_sub"]),
        )
        db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "id": sub_id, "points_awarded": points}), 200
    return redirect("/admin.html#approvals")


@api_bp.route("/admin/submissions/<int:sub_id>/reject", methods=["POST"])
def admin_reject_submission(sub_id: int):
    """Reject a pending submission (sets status to 'rejected', adds no points)."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Admin access required."}), 403

    db = get_db()
    db.execute("UPDATE submissions SET status = 'rejected', points = 0 WHERE id = ?", (sub_id,))
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "id": sub_id}), 200
    return redirect("/admin.html#approvals")


@api_bp.route("/admin/users/<int:user_id>", methods=["POST"])
def admin_update_user(user_id: int):
    """Update a person's name and set their total points directly."""
    user = session.get("user")
    if not _is_admin(user):
        return jsonify({"error": "Forbidden", "message": "Admin access required."}), 403

    payload = request.get_json(silent=True) or request.form
    name = (payload.get("name") or "").strip()
    pts_raw = payload.get("points", 0)

    if not name:
        abort(400, description="Name cannot be empty.")

    try:
        points = int(pts_raw)
        if points < 0:
            raise ValueError
    except ValueError:
        abort(400, description="'points' must be a whole number 0 or greater.")

    db = get_db()
    target = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        abort(404)

    db.execute(
        "UPDATE users SET name = ?, points = ? WHERE id = ?",
        (name[:60], points, user_id),
    )
    # Also update their display name on their submissions & comments
    db.execute(
        "UPDATE submissions SET user_name = ? WHERE user_sub = ?",
        (name[:60], target["sub"]),
    )
    db.execute(
        "UPDATE post_comments SET user_name = ? WHERE user_sub = ?",
        (name[:60], target["sub"]),
    )
    db.commit()

    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({"status": "success", "id": user_id, "name": name[:60], "points": points}), 200
    return redirect("/admin.html#people")