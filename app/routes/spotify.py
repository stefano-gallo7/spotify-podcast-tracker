import os
import secrets
import time
from datetime import timezone
from urllib.parse import urlencode

import requests
import spotipy
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOauthError

from app.db import get_session
from app.db_models import AppState, Show
from app.schemas import SpotifyAuthStatus, SpotifySearchResult
from app.spotify import (
    CACHE_PATH,
    REQUESTS_TIMEOUT,
    SpotifyAuthRevoked,
    _images,
    call_with_retry,
    clear_auth_failure,
    description_excerpt,
    make_auth_manager,
    make_client,
    remember_spotify_account,
)

load_dotenv()

router = APIRouter(prefix="/api/spotify", tags=["spotify"])

# Where Spotify sends the browser back after the in-app "Reconnect". Separate
# from SPOTIPY_REDIRECT_URI (the terminal login's), so both flows keep working;
# it must be registered in the Spotify Developer Dashboard. Spotify rejects
# `localhost` redirect URIs, hence 127.0.0.1.
WEB_REDIRECT_URI = os.getenv(
    "SPOTIFY_WEB_REDIRECT_URI", "http://127.0.0.1:8000/api/spotify/callback"
)
# Where the callback sends the browser once it's done.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# OAuth `state` values issued by /login and not yet used, with issue time. In
# memory: single user, single process — a restart mid-login just means retrying.
_STATE_TTL_SECONDS = 600
_pending_states: dict[str, float] = {}


@router.get("/search", response_model=list[SpotifySearchResult])
def search_shows(
    q: str = Query(..., min_length=1, description="Search text for Spotify's show catalogue"),
    session: Session = Depends(get_session),
):
    sp = make_client()
    response = call_with_retry(sp.search, q=q, type="show", limit=10)
    items = (response.get("shows") or {}).get("items") or []

    # Drop nulls (region-restricted entries come back as None).
    items = [item for item in items if item]

    # One batched lookup so each row knows whether it's already tracked — no N+1.
    uris = [item["uri"] for item in items]
    existing = set()
    if uris:
        rows = session.query(Show.uri).filter(Show.uri.in_(uris)).all()
        existing = {uri for (uri,) in rows}

    results = []
    for item in items:
        _, _, small = _images(item.get("images"))
        results.append(
            SpotifySearchResult(
                id=item["uri"].split(":")[-1],
                uri=item["uri"],
                name=item["name"],
                description_excerpt=description_excerpt(item),
                image_url_small=small,
                total_episodes=item.get("total_episodes"),
                already_in_library=item["uri"] in existing,
            )
        )
    return results


@router.get("/status", response_model=SpotifyAuthStatus)
def auth_status(session: Session = Depends(get_session)):
    """Report whether the stored Spotify login works.

    Free while healthy: just reads the flag that failing calls set. Only while
    flagged does it test the login — so a fix made outside the app (the terminal
    login) clears the banner on the next check. Still broken or unreachable →
    the flag stays.
    """
    state = session.query(AppState).first()
    if state is None or state.spotify_auth_error_at is None:
        return SpotifyAuthStatus(auth_ok=True)

    try:
        # Validates the cached token, refreshing it if expired — the exact step
        # that failed (a revoked login leaves an expired token in the cache).
        make_auth_manager().get_access_token(as_dict=False)
    except (SpotifyAuthRevoked, SpotifyOauthError, requests.exceptions.RequestException):
        return SpotifyAuthStatus(
            auth_ok=False,
            error_at=state.spotify_auth_error_at.replace(tzinfo=timezone.utc),
            message=state.spotify_auth_error,
        )
    clear_auth_failure()
    return SpotifyAuthStatus(auth_ok=True)


@router.get("/login")
def login():
    """Start the browser OAuth flow: redirect to Spotify's consent page."""
    issued = time.monotonic()
    for s, t in list(_pending_states.items()):
        if issued - t > _STATE_TTL_SECONDS:
            del _pending_states[s]
    state = secrets.token_urlsafe(16)
    _pending_states[state] = issued

    auth = make_auth_manager(redirect_uri=WEB_REDIRECT_URI)
    # show_dialog: always show the consent page, so it's visible which Spotify
    # account is being connected (and it can be switched).
    auth.show_dialog = True
    return RedirectResponse(auth.get_authorize_url(state))


def _back_to_frontend(**params) -> RedirectResponse:
    return RedirectResponse(f"{FRONTEND_URL}/?{urlencode(params)}")


@router.get("/callback")
def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: Session = Depends(get_session),
):
    """Spotify redirects here after consent: exchange the code, cache the token.

    The new login is held in memory until its account is checked: only the
    account the library belongs to may replace the shared token file. With no
    account on record yet, the first login sets it.
    """
    issued = _pending_states.pop(state, None) if state else None
    if issued is None or time.monotonic() - issued > _STATE_TTL_SECONDS:
        return _back_to_frontend(spotify="error", reason="invalid_state")
    if error or not code:
        # e.g. `access_denied` when "Cancel" is clicked on the consent page.
        return _back_to_frontend(spotify="error", reason=error or "missing_code")

    pending = MemoryCacheHandler()
    try:
        # check_cache=False: skip the (revoked) cached token and always exchange.
        access_token = make_auth_manager(
            redirect_uri=WEB_REDIRECT_URI, cache_handler=pending
        ).get_access_token(code, as_dict=False, check_cache=False)
        user = spotipy.Spotify(auth=access_token, requests_timeout=REQUESTS_TIMEOUT).current_user()
    except (SpotifyOauthError, SpotifyException, requests.exceptions.RequestException):
        return _back_to_frontend(spotify="error", reason="token_exchange_failed")

    expected = session.query(AppState.spotify_user_id).scalar()
    if expected and user["id"] != expected:
        return _back_to_frontend(spotify="error", reason="wrong_account")

    CacheFileHandler(cache_path=CACHE_PATH).save_token_to_cache(pending.get_cached_token())
    if not expected:
        remember_spotify_account(user["id"])
    clear_auth_failure()
    return _back_to_frontend(spotify="reconnected")
