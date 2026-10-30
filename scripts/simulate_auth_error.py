"""
Dev tool: fake a revoked Spotify login, to see the frontend's reconnect banner.

Backs up the real token cache, replaces it with an expired token whose refresh
token Spotify will reject (`invalid_grant` — exactly the real failure), and sets
the auth-error flag. The app then behaves as if the login had been revoked:
banner up, searches fail, scheduled runs abort. Reconnecting from the banner is
a genuine fix (it writes a fresh token).

    python -m scripts.simulate_auth_error            # break the login
    python -m scripts.simulate_auth_error --restore  # undo

`--restore` puts the backup back only if the fake token is still in place; if a
reconnect already replaced it, the backup is just discarded.
"""

import argparse
import json
import os
import time

from app.spotify import CACHE_PATH, SCOPE, clear_auth_failure, record_auth_failure

BACKUP_PATH = CACHE_PATH + ".bak"
FAKE_REFRESH_TOKEN = "simulated-revoked-refresh-token"


def _cache_is_fake() -> bool:
    try:
        with open(CACHE_PATH) as f:
            return json.load(f).get("refresh_token") == FAKE_REFRESH_TOKEN
    except (OSError, ValueError):
        return False


def simulate() -> None:
    if _cache_is_fake():
        print("Already simulating; run with --restore to undo.")
        return
    if os.path.exists(CACHE_PATH):
        os.replace(CACHE_PATH, BACKUP_PATH)
    fake = {
        "access_token": "simulated-expired-access-token",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": SCOPE,
        "expires_at": int(time.time()) - 60,  # expired → forces a refresh attempt
        "refresh_token": FAKE_REFRESH_TOKEN,
    }
    with open(CACHE_PATH, "w") as f:
        json.dump(fake, f)
    record_auth_failure("Simulated by scripts.simulate_auth_error.")
    print(f"Login broken on purpose (real token saved to {BACKUP_PATH}).")
    print("Switch to the app tab (or reload) to see the banner.")


def restore() -> None:
    if _cache_is_fake():
        if os.path.exists(BACKUP_PATH):
            os.replace(BACKUP_PATH, CACHE_PATH)
            print("Real token restored.")
        else:
            os.remove(CACHE_PATH)
            print("No backup to restore; fake token removed. Log in again to get a token.")
    elif os.path.exists(BACKUP_PATH):
        os.remove(BACKUP_PATH)
        print("Token was already replaced by a reconnect; backup discarded.")
    else:
        print("Nothing to restore.")
    clear_auth_failure()


def main():
    parser = argparse.ArgumentParser(description="Fake a revoked Spotify login (dev tool).")
    parser.add_argument("--restore", action="store_true", help="Undo the simulation.")
    args = parser.parse_args()
    restore() if args.restore else simulate()


if __name__ == "__main__":
    main()
