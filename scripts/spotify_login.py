"""
Log in to Spotify from the terminal and cache the token.

The fallback to the frontend's "Reconnect" button (`/api/spotify/login`): use it
for first-time setup, or if the backend isn't running. Discards the cached token
first, so a revoked one can't short-circuit the login, then runs spotipy's
interactive flow against `SPOTIPY_REDIRECT_URI` and clears the auth-error flag.

Unlike the in-app reconnect, it accepts *any* account and records it as the
library's account — this is the deliberate way to switch Spotify accounts.

    python -m scripts.spotify_login
"""

import os

from app.spotify import (
    CACHE_PATH,
    call_with_retry,
    clear_auth_failure,
    make_client,
    remember_spotify_account,
)


def main():
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)
    sp = make_client(interactive=True)
    user = call_with_retry(sp.current_user)
    remember_spotify_account(user["id"])
    clear_auth_failure()
    print(f"Logged in as {user.get('display_name') or user['id']}; token cached at {CACHE_PATH}")


if __name__ == "__main__":
    main()
