from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes import episodes, settings, shows, spotify, stats, tags
from app.scheduler import start_scheduler, stop_scheduler
from app.spotify import SpotifyAuthRevoked, record_auth_failure


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Spotify Podcast Tracker",
    description="Personal API for browsing my podcast listening library.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Any route that hits a dead Spotify login: flag it (the scheduler does the same
# on its side) and answer with a stable `code` the frontend turns into the
# reconnect banner. Sync handler → Starlette runs it in the threadpool.
@app.exception_handler(SpotifyAuthRevoked)
def spotify_auth_revoked(request: Request, exc: SpotifyAuthRevoked):
    record_auth_failure(str(exc))
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc), "code": "spotify_auth_revoked"},
    )


app.include_router(shows.router)
app.include_router(episodes.router)
app.include_router(settings.router)
app.include_router(spotify.router)
app.include_router(stats.router)
app.include_router(tags.router)


@app.get("/")
def root():
    return {"message": "Spotify Podcast Tracker API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
