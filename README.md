# HackCamp — Flask + HTML5/JS starter

A minimal, working basis for a Python Flask backend that talks to a vanilla
HTML5/JavaScript frontend over a JSON API.

```
backend/
  app.py              # App factory + entrypoint; also serves the frontend
  requirements.txt    # Python dependencies
  routes/
    api.py            # JSON API blueprint (/api/...)
frontend/
  index.html          # Single page UI
  css/styles.css
  js/api.js           # fetch wrapper for the API
  js/app.js           # UI logic (GET + POST examples)
```

## Run it

From the repository root:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start the server
python backend/app.py
```

Then open <http://127.0.0.1:5000>.

Alternatively, from the repository root with the virtualenv active:

```bash
flask --app backend.app run --debug
```

Flask serves both the JSON API and the static frontend, so there is no CORS
setup needed for the default workflow. CORS is still enabled on `/api/*` in
case you run the frontend from a separate dev server (e.g. Live Server) and
change `API_BASE` in `frontend/js/api.js` to `http://127.0.0.1:5000/api`.

## API endpoints

| Method | Path                 | Description                          |
| ------ | -------------------- | ------------------------------------ |
| Method | Path                        | Description                                    |
| ------ | --------------------------- | ---------------------------------------------- |
| GET    | `/api/health`               | Liveness probe, returns status JSON            |
| GET    | `/api/greeting?name=`       | Returns `{"message": "Hello, ...!"}`           |
| POST   | `/api/echo`                 | Echoes a JSON body back                        |
| GET    | `/api/auth/login`           | Starts Google OAuth sign-in (redirects to Google) |
| GET    | `/api/auth/callback`        | Google OAuth redirect handler (sets session)   |
| GET    | `/api/auth/user`            | Returns the signed-in user or 401              |
| POST   | `/api/auth/logout`          | Clears the session                             |
| GET    | `/api/protected`            | Example endpoint requiring sign-in (401 else)  |

Example:

```bash
curl http://127.0.0.1:5000/api/health
curl "http://127.0.0.1:5000/api/greeting?name=Ada"
curl -X POST http://127.0.0.1:5000/api/echo \
  -H "Content-Type: application/json" \
  -d '{"message":"hi"}'
```

## Google Sign-In setup

The app uses Google's server-side OAuth 2.0 flow, so no Google SDK is needed
on the frontend.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create an OAuth 2.0 Client ID (Web application).
3. Add `http://127.0.0.1:5000/api/auth/callback` as an **Authorized redirect URI**.
4. Create a `.env` file in the repository root (see
   [Environment variables](#environment-variables-env) below) and put the
   Client ID and Client Secret in `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
5. Generate a session secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   and set it as `FLASK_SECRET_KEY` in `.env`.
6. Restart the server and click **Sign in with Google**.

## Environment variables (`.env`)

All settings live in one `.env` file in the repository root (next to this
README). `backend/config.py` loads it when the server starts. `.env` is
gitignored, so each person keeps their own copy and real secrets never go in
this file or in git.

Copy this into `.env` and fill in the values marked `<...>`:

```ini
# Server
HOST=127.0.0.1
PORT=5000
FLASK_DEBUG=1

# Session cookie signing key (make one with:
#   python -c "import secrets; print(secrets.token_hex(32))")
FLASK_SECRET_KEY=<random 64-character hex string>

# Google sign-in (from Google Cloud Console > Credentials > OAuth 2.0 Client ID)
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/api/auth/callback

# Where to send people after they sign in
POST_LOGIN_REDIRECT=/

# Who can use the Admin page (comma-separated Google emails)
ADMIN_EMAILS=<you@gmail.com>,<teammate@gmail.com>
```

| Variable | Required | Default | What it does |
| --- | --- | --- | --- |
| `HOST` | No | `127.0.0.1` | Address the server listens on. (`FLASK_HOST` also works.) |
| `PORT` | No | `5000` | Port the server listens on. (`FLASK_PORT` also works.) |
| `FLASK_DEBUG` | No | `0` | `1` turns on debug mode and auto-reload. Use `0` when the site is shared. |
| `FLASK_SECRET_KEY` | Yes | a fixed dev key | Signs the session cookie that keeps people signed in. Keep it secret and random. (`SECRET_KEY` also works.) |
| `GOOGLE_CLIENT_ID` | Yes | none | OAuth client ID for "Sign in with Google". Without it, `/api/auth/login` returns an error. |
| `GOOGLE_CLIENT_SECRET` | Yes | none | OAuth client secret that goes with the client ID. Keep it secret. |
| `GOOGLE_REDIRECT_URI` | No | `http://HOST:PORT/api/auth/callback` | Where Google sends people back after sign-in. Must exactly match an Authorized redirect URI in Google Cloud Console. |
| `POST_LOGIN_REDIRECT` | No | `/` | Page to open after a successful sign-in. |
| `ADMIN_EMAILS` | Yes, before sharing the site | empty | Comma-separated emails that get the Admin page. **If it's empty, every signed-in user is treated as an admin** (handy for testing, unsafe for real use). |
| `CORS_ORIGINS` | No | `http://HOST:PORT` | Other sites allowed to call `/api/*`. Only needed if the front end runs on a different server. |
| `DATABASE_PATH` | No | `backend/cleanics.db` | Where the SQLite database file is stored. |
| `UPLOAD_FOLDER` | No | `backend/uploads` | Where uploaded before/after photos are saved. |
| `FLASK_ENV` | No | `default` (development) | `production` turns off debug and makes the session cookie HTTPS-only. |

## Where to add things

- **New endpoint:** add a route in `backend/routes/api.py` (or a new blueprint
  in `backend/routes/` and register it in `create_app`).
- **New API call:** add a small function in `frontend/js/api.js`, then call it
  from `frontend/js/app.js`.
- **Config:** environment variables are read in `backend/config.py`. See
  [Environment variables](#environment-variables-env).
