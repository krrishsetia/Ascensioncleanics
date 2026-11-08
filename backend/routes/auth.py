"""Google OAuth 2.0 sign-in routes."""
import os
from flask import Blueprint, current_app, jsonify, redirect, request, session
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Allow plain HTTP on 127.0.0.1 and prevent scope-order mismatch exceptions
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

auth_bp = Blueprint("auth", __name__)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def _build_flow(redirect_uri: str | None = None, state: str | None = None) -> Flow:
    """Build a Google OAuth flow from environment-configured credentials."""
    client_id = current_app.config["GOOGLE_CLIENT_ID"].strip()
    # Strip any accidental leading colon or whitespace from .env
    client_secret = current_app.config["GOOGLE_CLIENT_SECRET"].strip().lstrip(":")
    resolved_redirect = (redirect_uri or current_app.config["GOOGLE_REDIRECT_URI"]).strip()

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [resolved_redirect],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=resolved_redirect,
        state=state,
    )


@auth_bp.get("/login")
def login():
    """Start the Google OAuth flow by redirecting the user to Google."""
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return jsonify(error="Google OAuth is not configured"), 500

    flow = _build_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Bind this browser session to the OAuth state and PKCE code_verifier
    session["oauth_state"] = state
    session["code_verifier"] = getattr(flow, "code_verifier", None)
    session.permanent = True
    return redirect(authorization_url)


@auth_bp.get("/callback")
def callback():
    """Handle the redirect from Google after the user signs in (or cancels)."""
    error = request.args.get("error")
    if error:
        description = request.args.get("error_description", error)
        current_app.logger.warning("Google OAuth error: %s", description)
        return jsonify(error=f"Google sign-in cancelled: {description}"), 400

    state = session.pop("oauth_state", None)
    code_verifier = session.pop("code_verifier", None)

    if not state or state != request.args.get("state"):
        return jsonify(error="Invalid OAuth state"), 400

    flow = _build_flow(state=state)
    # Restore PKCE code_verifier generated during /login
    if code_verifier:
        flow.code_verifier = code_verifier

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as exc:
        current_app.logger.error("Token exchange failed: %s", exc)
        return jsonify(
            error="Failed to exchange authorization code",
            details=str(exc),
        ), 400

    credentials = flow.credentials
    if not credentials.id_token:
        return jsonify(error="No ID token returned by Google"), 400

    try:
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            current_app.config["GOOGLE_CLIENT_ID"].strip(),
            clock_skew_in_seconds=10,
        )
    except ValueError as exc:
        current_app.logger.error("ID token verification failed: %s", exc)
        return jsonify(error="Invalid ID token", details=str(exc)), 400

    session["user"] = {
        "sub": id_info["sub"],
        "email": id_info.get("email"),
        "name": id_info.get("name"),
        "picture": id_info.get("picture"),
        "email_verified": id_info.get("email_verified", False),
    }
    session.permanent = True

    return redirect(current_app.config.get("POST_LOGIN_REDIRECT", "/"))


@auth_bp.get("/user")
def user():
    """Return the signed-in user's profile and role, or 401 when nobody is signed in."""
    user_info = session.get("user")
    if not user_info:
        return jsonify(error="Not authenticated"), 401

    admin_emails = current_app.config.get("ADMIN_EMAILS", [])
    user_email = (user_info.get("email") or "").lower()
    # If ADMIN_EMAILS is not configured, default to admin so you can test all features
    is_admin = (user_email in admin_emails) if admin_emails else True

    return jsonify(
        user=user_info,
        role="admin" if is_admin else "member",
        authenticated=True,
    )


@auth_bp.post("/logout")
def logout():
    """Clear the session and sign the user out."""
    session.clear()
    return jsonify(authenticated=False)