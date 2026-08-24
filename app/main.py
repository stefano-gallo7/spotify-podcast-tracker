from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import episodes, settings, shows, spotify, stats
from app.scheduler import start_scheduler, stop_scheduler


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

app.include_router(shows.router)
app.include_router(episodes.router)
app.include_router(settings.router)
app.include_router(spotify.router)
app.include_router(stats.router)


@app.get("/")
def root():
    return {"message": "Spotify Podcast Tracker API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
