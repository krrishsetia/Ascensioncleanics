"""SQLite database initialization and connection management."""
import sqlite3
from datetime import datetime, timezone
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection for the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None) -> None:
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def upsert_user(sub: str, name: str, email: str) -> dict:
    """Ensure a signed-in Google user exists in the users table and return their row."""
    db = get_db()
    existing = db.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone()
    if existing:
        # Keep email updated, but preserve any admin-edited name and points
        db.execute("UPDATE users SET email = ? WHERE sub = ?", (email, sub))
        db.commit()
        return dict(db.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone())

    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO users (sub, name, email, points, created_at)
        VALUES (?, ?, ?, 0, ?)
        """,
        (sub, name or email or "Anonymous", email or "", now),
    )
    db.commit()
    return dict(db.execute("SELECT * FROM users WHERE sub = ?", (sub,)).fetchone())


def init_db(app) -> None:
    """Create and auto-migrate all required tables."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sub TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                points INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_sub TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_email TEXT,
                description TEXT NOT NULL,
                cleaned_on TEXT NOT NULL,
                before_image_url TEXT NOT NULL,
                after_image_url TEXT NOT NULL,
                points INTEGER DEFAULT 10,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS post_likes (
                post_id INTEGER NOT NULL,
                user_sub TEXT NOT NULL,
                PRIMARY KEY (post_id, user_sub),
                FOREIGN KEY (post_id) REFERENCES submissions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS post_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_sub TEXT NOT NULL,
                user_name TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES submissions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                due_on TEXT NOT NULL,
                pts_worth INTEGER NOT NULL CHECK(pts_worth BETWEEN 1 AND 100),
                description TEXT NOT NULL,
                photo_url TEXT,
                status INTEGER NOT NULL DEFAULT 0 CHECK(status IN (0, 1, 2)),
                created_at TEXT NOT NULL
            );
            """
        )

        # Auto-migrate existing submissions table if columns were added later
        sub_cols = [
            col["name"]
            for col in db.execute("PRAGMA table_info(submissions)").fetchall()
        ]
        if "points" not in sub_cols:
            db.execute("ALTER TABLE submissions ADD COLUMN points INTEGER DEFAULT 10")
        if "status" not in sub_cols:
            db.execute(
                "ALTER TABLE submissions ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'"
            )

        db.commit()