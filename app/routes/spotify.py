from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.db_models import Show
from app.schemas import SpotifySearchResult
from app.spotify import _images, call_with_retry, description_excerpt, make_client

router = APIRouter(prefix="/api/spotify", tags=["spotify"])


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
