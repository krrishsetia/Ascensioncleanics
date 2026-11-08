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
4. Copy the Client ID and Client Secret into `.env` (copy from `.env.example`):
   ```bash
   cp .env.example .env
   # edit .env with your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
   ```
5. Generate a session secret:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   and set it as `FLASK_SECRET_KEY` in `.env`.
6. Restart the server and click **Sign in with Google**.

## Where to add things

- **New endpoint:** add a route in `backend/routes/api.py` (or a new blueprint
  in `backend/routes/` and register it in `create_app`).
- **New API call:** add a small function in `frontend/js/api.js`, then call it
  from `frontend/js/app.js`.
- **Config:** environment variables `HOST`, `PORT`, and `FLASK_DEBUG` are read
  in `backend/app.py`. See `.env.example`.
