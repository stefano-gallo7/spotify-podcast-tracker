from fastapi import FastAPI

from app.routes import episodes, shows

app = FastAPI(
    title="Spotify Podcast Tracker",
    description="Personal API for browsing my podcast listening library.",
    version="0.1.0",
)

app.include_router(shows.router)
app.include_router(episodes.router)


@app.get("/")
def root():
    return {"message": "Spotify Podcast Tracker API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}
