"""SQLite database initialization and connection management."""
import sqlite3
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


def init_db(app) -> None:
    """Create the submissions, likes, and comments tables if they do not exist."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.executescript(
            """
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
            """
        )
        db.commit()