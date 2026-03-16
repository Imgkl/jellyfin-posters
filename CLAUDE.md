# CLAUDE.md

## Project Overview

Jellyfin Posters is a FastAPI web app that lets users review and replace movie artwork (posters, backdrops, logos) on a Jellyfin media server. The frontend is a vanilla JavaScript SPA served as static files; the backend proxies all Jellyfin API calls and tracks review progress in SQLite.

## Directory Structure

```
app/
  main.py            # FastAPI app, lifespan, route mounting, SPA fallback
  config.py          # Pydantic Settings (reads .env)
  state.py           # Shared AppState (httpx client, Jellyfin URL)
  dependencies.py    # FastAPI dependency injection
  routers/           # Route modules: auth, movies, images, library, progress, data
  models/schemas.py  # Pydantic request/response models
  services/
    jellyfin_client.py  # Async httpx wrapper for Jellyfin REST API
    progress_db.py      # aiosqlite CRUD for progress.db
  static/
    index.html       # SPA entry point
    css/style.css    # Dark theme styles
    js/app.js        # Main app logic + keyboard shortcuts
    js/carousel.js   # ImageGrid class for thumbnail selection
    js/api.js        # Fetch wrapper
```

## Running Locally

```bash
cp .env.example .env   # set JELLYFIN_URL
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tech Stack

- **Backend:** FastAPI, httpx (async), aiosqlite, pydantic-settings
- **Frontend:** Vanilla JS with ES6+ classes — no framework, no build step
- **Database:** SQLite (`progress.db`) — single table `progress`
- **Python:** 3.12

## Key Patterns

- All I/O is async (`async def` endpoints, `httpx.AsyncClient`, `aiosqlite`)
- Pydantic models for all request/response schemas (`app/models/schemas.py`)
- No frontend framework — DOM manipulation in `app.js`, reusable `ImageGrid` class in `carousel.js`
- Static files served by FastAPI with an SPA catch-all fallback route
- Jellyfin auth token stored in `AppState` and passed via dependency injection

## Environment

Requires a `.env` file with at minimum:
```
JELLYFIN_URL=http://your-jellyfin:8096
```
See `.env.example` for all options. `JELLYFIN_USERNAME`/`JELLYFIN_PASSWORD` are optional (auto-login).

## Testing

No test suite currently exists.

## Code Style

- Python: no type stubs, standard FastAPI conventions
- JavaScript: vanilla ES6+ with classes, no transpilation or bundling
- CSS: custom properties for theming, dark theme only
